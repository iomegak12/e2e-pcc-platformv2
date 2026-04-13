#!/usr/bin/env python3
"""
Guidelines Verification Script
Checks that all required clinical guideline files (PDF or TXT) are present and valid.
"""

import os
import sys
from pathlib import Path


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


REQUIRED_FILES = [
    "NICE_NG203_Anaemia",
    "NICE_NG28_Diabetes",
    "WHO_Anaemia_Protocol",
]

MIN_FILE_SIZE_PDF = 100 * 1024  # 100 KB minimum for PDFs
MIN_FILE_SIZE_TXT = 1024  # 1 KB minimum for TXT files


def main():
    """Main verification."""
    print_header("Clinical Guidelines Verification")
    
    # Check both possible locations
    project_root = Path(__file__).parent.parent
    possible_dirs = [
        project_root / "guidelines",
        project_root / "data" / "guidelines",
    ]
    
    guidelines_dir = None
    for dir_path in possible_dirs:
        if dir_path.exists():
            guidelines_dir = dir_path
            break
    
    if not guidelines_dir:
        print(f"✗ Guidelines directory not found in:")
        for dir_path in possible_dirs:
            print(f"  - {dir_path}")
        print(f"\nRun: python vector_store/download_guidelines.py")
        sys.exit(1)
    
    print(f"Checking: {guidelines_dir}\n")
    
    found_files = []
    missing_files = []
    invalid_files = []
    
    for base_filename in REQUIRED_FILES:
        # Check for both PDF and TXT
        pdf_path = guidelines_dir / f"{base_filename}.pdf"
        txt_path = guidelines_dir / f"{base_filename}.txt"
        
        found = False
        
        if pdf_path.exists():
            file_size = pdf_path.stat().st_size
            if file_size < MIN_FILE_SIZE_PDF:
                print(f"⚠  Too small: {pdf_path.name} ({file_size} bytes)")
                invalid_files.append(pdf_path.name)
            else:
                print(f"✓ Found: {pdf_path.name} ({file_size // 1024} KB)")
                found_files.append(pdf_path.name)
                found = True
        
        if txt_path.exists():
            file_size = txt_path.stat().st_size
            if file_size < MIN_FILE_SIZE_TXT:
                print(f"⚠  Too small: {txt_path.name} ({file_size} bytes)")
                invalid_files.append(txt_path.name)
            else:
                print(f"✓ Found: {txt_path.name} ({file_size // 1024} KB, text format)")
                found_files.append(txt_path.name)
                found = True
        
        if not found:
            print(f"✗ Missing: {base_filename}.pdf or {base_filename}.txt")
            missing_files.append(base_filename)
    
    # Summary
    print(f"\n{'─'*70}")
    print(f"Found: {len(found_files)}/{len(REQUIRED_FILES)} required files")
    
    if missing_files:
        print(f"\nMissing files:")
        for f in missing_files:
            print(f"  - {f}.pdf or {f}.txt")
        print(f"\nSee data/guidelines/registry.md for download instructions")
        print(f"Or use existing TXT samples in guidelines/ directory")
    
    if invalid_files:
        print(f"\nInvalid files (too small):")
        for f in invalid_files:
            print(f"  - {f}")
    
    if len(found_files) >= len(REQUIRED_FILES):
        print(f"\n✓ All guideline files present and valid!")
        print(f"\nNext step: python scripts/run_data_pipeline.py --stage vector")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
