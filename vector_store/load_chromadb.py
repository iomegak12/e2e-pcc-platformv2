#!/usr/bin/env python3
"""
ChromaDB Vector Store Loader
Processes clinical guideline PDFs into embeddings and loads into ChromaDB.

Process:
1. Extract text from PDFs
2. Chunk text (600 tokens, 60 token overlap)
3. Generate embeddings with OpenAI text-embedding-3-small
4. Load into ChromaDB with metadata
"""

import os
import sys
import warnings

# Disable ChromaDB telemetry BEFORE importing chromadb
os.environ['ANONYMIZED_TELEMETRY'] = 'False'
os.environ['CHROMA_TELEMETRY_IMPL'] = 'none'

# Suppress stderr for telemetry warnings
import contextlib
import io

from pathlib import Path
from typing import List, Dict
import tiktoken
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 600))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 60))
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
CHROMADB_HOST = os.getenv('CHROMADB_HOST', 'localhost')
CHROMADB_PORT = int(os.getenv('CHROMADB_PORT', 8200))


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def extract_text_from_pdf(pdf_path: Path) -> List[Dict]:
    """Extract text from PDF, preserving page numbers."""
    try:
        import pypdf
        
        pages = []
        with open(pdf_path, 'rb') as file:
            pdf = pypdf.PdfReader(file)
            
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text.strip():
                    pages.append({
                        'page_number': page_num,
                        'text': text
                    })
        
        print(f"  Extracted {len(pages)} pages from {pdf_path.name}")
        return pages
    
    except Exception as e:
        print(f"✗ Error extracting {pdf_path.name}: {e}")
        return []


def extract_text_from_txt(txt_path: Path) -> List[Dict]:
    """Extract text from text file, simulating page structure."""
    try:
        with open(txt_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Split by common section markers or approximate page size
        # For simplicity, split into chunks of ~2000 characters as "pages"
        page_size = 2000
        pages = []
        
        # Try to split by headers first (markdown-style)
        sections = content.split('\n## ')
        if len(sections) == 1:
            # No markdown headers, split by character count
            for i in range(0, len(content), page_size):
                page_text = content[i:i+page_size]
                if page_text.strip():
                    pages.append({
                        'page_number': (i // page_size) + 1,
                        'text': page_text
                    })
        else:
            # Use sections as pages
            for idx, section in enumerate(sections, 1):
                if section.strip():
                    # Re-add the header marker
                    section_text = ('## ' + section) if idx > 1 else section
                    pages.append({
                        'page_number': idx,
                        'text': section_text
                    })
        
        print(f"  Extracted {len(pages)} sections from {txt_path.name}")
        return pages
    
    except Exception as e:
        print(f"✗ Error extracting {txt_path.name}: {e}")
        return []


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Chunk text by token count with overlap."""
    try:
        # Initialize tokenizer
        encoding = tiktoken.get_encoding("cl100k_base")
        
        # Tokenize
        tokens = encoding.encode(text)
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            end = start + chunk_size
            chunk_tokens = tokens[start:end]
            chunk_text = encoding.decode(chunk_tokens)
            chunks.append(chunk_text)
            
            start += chunk_size - overlap
        
        return chunks
    
    except Exception as e:
        print(f"⚠  Chunking error: {e}")
        # Fallback: character-based chunking
        chunk_chars = chunk_size * 4  # Approximate chars per token
        overlap_chars = overlap * 4
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_chars
            chunks.append(text[start:end])
            start += chunk_chars - overlap_chars
        
        return chunks


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using OpenAI API."""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Batch embed (up to 2048 texts at a time)
        embeddings = []
        batch_size = 100
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch
            )
            
            batch_embeddings = [item.embedding for item in response.data]
            embeddings.extend(batch_embeddings)
            
            print(f"    Generated embeddings {i+1}-{min(i+batch_size, len(texts))}/{len(texts)}")
        
        return embeddings
    
    except Exception as e:
        print(f"✗ Embedding error: {e}")
        raise


def load_into_chromadb(chunks_with_metadata: List[Dict]):
    """Load chunks with embeddings into ChromaDB."""
    try:
        # Suppress ChromaDB telemetry errors (known bug in library)
        stderr_suppressor = contextlib.redirect_stderr(io.StringIO())
        
        import chromadb
        
        # Use PersistentClient (local storage) to avoid API version issues
        # Store in project directory for now
        chroma_path = Path(__file__).parent.parent / "data" / "chromadb"
        chroma_path.mkdir(parents=True, exist_ok=True)
        
        with stderr_suppressor:
            client = chromadb.PersistentClient(path=str(chroma_path))
        print(f"  Using local ChromaDB storage: {chroma_path}")
        
        # Get or create collection
        collection_name = "clinical_guidelines"
        
        # Delete existing collection if it exists (fresh load)
        try:
            with stderr_suppressor:
                client.delete_collection(collection_name)
            print(f"  Deleted existing collection: {collection_name}")
        except:
            pass
        
        with stderr_suppressor:
            collection = client.create_collection(
                name=collection_name,
                metadata={"description": "Clinical guidelines for RAG"}
            )
        
        print(f"  Created collection: {collection_name}")
        
        # Prepare data for insertion
        documents = [c['text'] for c in chunks_with_metadata]
        metadatas = [{
            'source': c['source'],
            'page': c['page'],
            'chunk_index': c['chunk_index'],
            'topics': c['topics']
        } for c in chunks_with_metadata]
        ids = [f"{c['source']}_p{c['page']}_c{c['chunk_index']}" for c in chunks_with_metadata]
        
        # Generate embeddings
        print(f"  Generating embeddings for {len(documents)} chunks...")
        embeddings = generate_embeddings(documents)
        
        # Insert into ChromaDB
        batch_size = 500
        for i in range(0, len(documents), batch_size):
            end = min(i + batch_size, len(documents))
            
            # Suppress telemetry errors
            with contextlib.redirect_stderr(io.StringIO()):
                collection.add(
                    documents=documents[i:end],
                    metadatas=metadatas[i:end],
                    ids=ids[i:end],
                    embeddings=embeddings[i:end]
                )
            
            print(f"    Loaded chunks {i+1}-{end}/{len(documents)}")
        
        print(f"✓ Loaded {len(documents)} chunks into ChromaDB")
        
        return collection
    
    except Exception as e:
        print(f"✗ ChromaDB loading error: {e}")
        raise


def test_retrieval(collection, query: str, n_results: int = 5):
    """Test retrieval with a sample query using OpenAI embeddings."""
    try:
        print(f"\n  Testing query: '{query}'")
        
        # Generate query embedding using the same OpenAI model
        query_embedding = generate_embeddings([query])[0]
        
        # Suppress telemetry errors
        with contextlib.redirect_stderr(io.StringIO()):
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
        
        if results['documents'] and results['documents'][0]:
            print(f"  ✓ Retrieved {len(results['documents'][0])} results")
            for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
                print(f"\n  Result {i}:")
                print(f"    Source: {metadata['source']}, Page: {metadata['page']}")
                print(f"    Snippet: {doc[:150]}...")
        else:
            print(f"  ⚠  No results found")
    
    except Exception as e:
        print(f"  ✗ Retrieval test failed: {e}")


def main():
    """Main execution."""
    print_header("ChromaDB Vector Store Loader")
    
    # Find guidelines directory
    guidelines_dir = Path(__file__).parent.parent / "guidelines"
    
    if not guidelines_dir.exists():
        # Try alternate location
        guidelines_dir = Path(__file__).parent.parent / "data" / "guidelines"
    
    if not guidelines_dir.exists():
        print(f"✗ Guidelines directory not found: {guidelines_dir}")
        sys.exit(1)
    
    # Find PDF and TXT files
    pdf_files = list(guidelines_dir.glob("*.pdf"))
    txt_files = list(guidelines_dir.glob("*.txt"))
    all_files = pdf_files + txt_files
    
    if not all_files:
        print(f"✗ No PDF or TXT files found in {guidelines_dir}")
        print("  Run: python vector_store/download_guidelines.py")
        sys.exit(1)
    
    print(f"Found {len(pdf_files)} PDF files and {len(txt_files)} TXT files")
    
    # Process each file
    all_chunks = []
    
    for file_path in all_files:
        print(f"\nProcessing: {file_path.name}")
        
        # Extract text based on file type
        if file_path.suffix.lower() == '.pdf':
            pages = extract_text_from_pdf(file_path)
        else:  # .txt
            pages = extract_text_from_txt(file_path)
        
        if not pages:
            continue
        
        # Chunk each page
        for page_data in pages:
            text_chunks = chunk_text(page_data['text'], CHUNK_SIZE, CHUNK_OVERLAP)
            
            for chunk_index, chunk_content in enumerate(text_chunks):
                if len(chunk_content.strip()) < 50:  # Skip very small chunks
                    continue
                
                all_chunks.append({
                    'text': chunk_content,
                    'source': file_path.stem,
                    'page': page_data['page_number'],
                    'chunk_index': chunk_index,
                    'topics': get_topics_from_filename(file_path.stem)
                })
        
        print(f"  Created {len([c for c in all_chunks if c['source'] == file_path.stem])} chunks")
    
    print(f"\n✓ Total chunks created: {len(all_chunks)}")
    
    # Load into ChromaDB
    print(f"\nLoading into ChromaDB...")
    print(f"  Host: {CHROMADB_HOST}:{CHROMADB_PORT}")
    print(f"  Embedding model: {EMBEDDING_MODEL}")
    
    collection = load_into_chromadb(all_chunks)
    
    # Test retrieval
    print_header("Testing Retrieval")
    
    test_queries = [
        "iron deficiency anaemia treatment oral versus intravenous",
        "chronic kidney disease stage 3 iron absorption",
        "metformin contraindications renal impairment eGFR",
    ]
    
    for query in test_queries:
        test_retrieval(collection, query)
    
    print_header("Vector Store Loading Complete")
    print(f"✓ Loaded {len(all_chunks)} chunks into ChromaDB")
    print(f"✓ Collection: clinical_guidelines")
    print(f"\nNext step: Build agents to use this vector store")


def get_topics_from_filename(filename: str) -> str:
    """Extract topic tags from filename."""
    topic_map = {
        'anaemia': 'iron deficiency, anaemia, ferritin, hemoglobin',
        'diabetes': 'type 2 diabetes, metformin, glucose, HbA1c',
        'kidney': 'chronic kidney disease, CKD, eGFR, creatinine, nephrology',
        'ng203': 'ckd, anaemia, iron',
        'ng28': 'diabetes',
        'who': 'iron supplementation',
    }
    
    filename_lower = filename.lower()
    topics = []
    
    for key, tags in topic_map.items():
        if key in filename_lower:
            topics.append(tags)
    
    return ', '.join(topics) if topics else 'general'


if __name__ == "__main__":
    main()
