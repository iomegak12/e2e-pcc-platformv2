#!/usr/bin/env python3
"""
Clinical Guidelines Downloader
Downloads publicly available clinical guideline PDFs for the vector store.

Guidelines to download:
- NICE guidelines (NG203, NG28, CG182)
- WHO primary care protocols
- BNF drug monographs (public excerpts)
"""

import os
import sys
from pathlib import Path
import requests

def print_header(text: str):
    """Print formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


# Clinical guideline URLs (publicly accessible versions)
GUIDELINES = {
    "NICE_NG203_Anaemia.pdf": {
        "url": "https://www.nice.org.uk/guidance/ng203",
        "title": "NICE Guideline NG203 - Chronic kidney disease: assessment and management",
        "manual": True  # Requires manual download
    },
    "NICE_NG28_Diabetes.pdf": {
        "url": "https://www.nice.org.uk/guidance/ng28",
        "title": "NICE Guideline NG28 - Type 2 diabetes in adults: management",
        "manual": True
    },
    "WHO_Anaemia_Protocol.pdf": {
        "url": "https://www.who.int/publications/i/item/9789241549523",
        "title": "WHO - Guideline: Daily iron supplementation in adult women and adolescent girls",
        "manual": True
    },
}

def create_guidelines_directory():
    """Create guidelines directory if it doesn't exist."""
    guidelines_dir = Path(__file__).parent.parent / "guidelines"
    guidelines_dir.mkdir(parents=True, exist_ok=True)
    return guidelines_dir


def create_registry_file(guidelines_dir: Path):
    """Create registry markdown file documenting all guidelines."""
    registry_content = """# Clinical Guidelines Registry

This directory contains clinical guideline PDFs used for the vector store (RAG).

## Guidelines

### NICE (National Institute for Health and Care Excellence)

| Guideline | Title | Publication Year | Topics |
|-----------|-------|------------------|--------|
| NG203 | Chronic kidney disease: assessment and management | 2021 | CKD, iron deficiency, anaemia |
| NG28 | Type 2 diabetes in adults: management | 2015 (updated 2022) | Diabetes, metformin, lifestyle |
| CG182 | Chronic kidney disease in adults: assessment and management | 2014 | CKD stages, monitoring |

### WHO (World Health Organization)

| Guideline | Title | Publication Year | Topics |
|-----------|-------|------------------|--------|
| Anaemia Protocol | Daily iron supplementation | 2016 | Iron deficiency, supplementation |

### BNF (British National Formulary)

| Drug Monograph | Topics |
|----------------|--------|
| Iron Sucrose | IV iron, dosing, contraindications |
| Ferrous Sulphate | Oral iron, side effects |
| Metformin | Diabetes, renal dosing |
| Lisinopril | ACE inhibitor, kidney protection |
| Amlodipine | Calcium channel blocker, hypertension |

## Download Instructions

Most clinical guidelines require manual download due to terms of service:

### NICE Guidelines
1. Visit https://www.nice.org.uk/guidance/ng203
2. Click "Download the full guideline" (PDF)
3. Save to this directory as `NICE_NG203_Anaemia.pdf`
4. Repeat for NG28 and CG182

### WHO Guidelines
1. Visit https://www.who.int/publications
2. Search for specific guideline
3. Download PDF version
4. Save to this directory

### BNF Monographs
1. Visit https://bnf.nice.org.uk/
2. Search for drug name
3. Print to PDF or save page
4. Save to this directory

## Verification

After downloading, verify PDFs:
- Text is selectable (not scanned images)
- Complete document (not truncated)
- Readable file size (> 100 KB typically)

Run verification:
```bash
python vector_store/verify_guidelines.py
```
"""
    
    registry_path = guidelines_dir / "registry.md"
    with open(registry_path, 'w', encoding='utf-8') as f:
        f.write(registry_content)
    
    print(f"✓ Created registry: {registry_path}")


def main():
    """Main execution."""
    print_header("Clinical Guidelines Downloader")
    
    # Create directory
    guidelines_dir = create_guidelines_directory()
    print(f"Guidelines directory: {guidelines_dir}")
    
    # Create registry
    create_registry_file(guidelines_dir)
    
    # Display manual download instructions
    print("\n" + "="*70)
    print("  MANUAL DOWNLOAD REQUIRED")
    print("="*70)
    print("\nClinical guidelines must be downloaded manually due to copyright and")
    print("terms of service. Follow these steps:\n")
    
    for i, (filename, info) in enumerate(GUIDELINES.items(), 1):
        print(f"{i}. {info['title']}")
        print(f"   URL: {info['url']}")
        print(f"   Save as: {guidelines_dir / filename}")
        print()
    
    print("See registry.md for detailed download instructions.")
    print(f"\nAfter downloading, verify with:")
    print(f"  python vector_store/verify_guidelines.py")
    
    print("\n✓ Setup complete - ready for manual downloads")


if __name__ == "__main__":
    main()
