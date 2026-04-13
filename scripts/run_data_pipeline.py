#!/usr/bin/env python3
"""
Data Pipeline Orchestrator
Master script to run the complete data synthesis pipeline.

Stages:
1. validate    - Check environment and prerequisites
2. synthea     - Generate FHIR synthetic data
3. schema      - Create database schema
4. transform   - Transform FHIR to SQL tables
5. faker       - Generate operational data
6. s3          - Upload FHIR bundles to S3
7. vector      - Load clinical guidelines into ChromaDB
8. verify      - Run data quality tests

Usage:
  python scripts/run_data_pipeline.py                    # Run all stages
  python scripts/run_data_pipeline.py --stage synthea    # Run single stage
  python scripts/run_data_pipeline.py --from transform   # Run from stage onward
"""

import os
import sys
import argparse
import subprocess
import time
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Stage definitions
STAGES = [
    {
        'name': 'validate',
        'description': 'Validate environment and prerequisites',
        'script': PROJECT_ROOT / 'scripts' / 'verify_environment.py',
        'args': [],
        'required': True
    },
    {
        'name': 'synthea',
        'description': 'Generate FHIR synthetic data with Synthea',
        'script': PROJECT_ROOT / 'data' / 'synthea' / 'run_synthea.py',
        'args': [],
        'required': True
    },
    {
        'name': 'schema',
        'description': 'Create PostgreSQL database schema',
        'script': None,  # SQL execution
        'sql_files': [
            PROJECT_ROOT / 'data' / 'schemas' / '001_initial_schema.sql',
            PROJECT_ROOT / 'data' / 'schemas' / '002_analytics_indexes.sql'
        ],
        'required': True
    },
    {
        'name': 'transform',
        'description': 'Transform FHIR to relational tables',
        'script': PROJECT_ROOT / 'data' / 'seeds' / 'transform_fhir.py',
        'args': [],
        'required': True
    },
    {
        'name': 'faker',
        'description': 'Generate operational data (clinicians, pharmacy, etc.)',
        'scripts': [
            PROJECT_ROOT / 'data' / 'seeds' / 'generate_clinicians.py',
            PROJECT_ROOT / 'data' / 'seeds' / 'generate_pharmacy_events.py',
            PROJECT_ROOT / 'data' / 'seeds' / 'generate_discharge_plans.py',
            PROJECT_ROOT / 'data' / 'seeds' / 'generate_wearables.py',
        ],
        'required': True
    },
    {
        'name': 's3',
        'description': 'Upload FHIR bundles to S3',
        'script': PROJECT_ROOT / 'data' / 'seeds' / 'upload_to_s3.py',
        'args': [],
        'required': False  # Optional for local development
    },
    {
        'name': 'vector',
        'description': 'Load clinical guidelines into ChromaDB',
        'script': PROJECT_ROOT / 'vector_store' / 'load_chromadb.py',
        'args': [],
        'required': True
    },
    {
        'name': 'verify',
        'description': 'Run data quality and analytics tests',
        'scripts': [
            PROJECT_ROOT / 'tests' / 'integration' / 'test_data_quality.py',
            PROJECT_ROOT / 'tests' / 'integration' / 'test_sql_queries.py',
        ],
        'required': False  # Optional verification
    }
]


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_stage_header(stage_num: int, total: int, stage_name: str, description: str):
    """Print stage start header."""
    print(f"\n{'-'*70}")
    print(f"  STAGE {stage_num}/{total}: {stage_name.upper()}")
    print(f"  {description}")
    print(f"{'-'*70}\n")


def run_python_script(script_path: Path, args: List[str] = None) -> bool:
    """Run a Python script and return success status."""
    try:
        # Detect virtual environment Python
        venv_python = None
        if os.getenv('VIRTUAL_ENV'):
            # Virtual environment is activated
            venv_python = os.path.join(os.getenv('VIRTUAL_ENV'), 'Scripts', 'python.exe')
        elif (PROJECT_ROOT / '.venv').exists():
            # Check for .venv in project root
            venv_python = str(PROJECT_ROOT / '.venv' / 'Scripts' / 'python.exe')
        
        python_exe = venv_python if venv_python and Path(venv_python).exists() else sys.executable
        
        cmd = [python_exe, str(script_path)]
        if args:
            cmd.extend(args)
        
        print(f"  Running: {script_path.name}")
        
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=False,
            text=True
        )
        
        print(f"  ✓ Completed: {script_path.name}\n")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed: {script_path.name}")
        print(f"  Error: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error running {script_path.name}: {e}")
        return False


def run_sql_files(sql_files: List[Path]) -> bool:
    """Execute SQL files against PostgreSQL."""
    try:
        import psycopg2
        
        # Connection parameters from environment
        conn_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'healthcare_pcc'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
        }
        
        print(f"  Connecting to PostgreSQL: {conn_params['host']}:{conn_params['port']}")
        
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        cursor = conn.cursor()
        
        for sql_file in sql_files:
            if not sql_file.exists():
                print(f"  ✗ SQL file not found: {sql_file}")
                return False
            
            print(f"  Executing: {sql_file.name}")
            
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            cursor.execute(sql_content)
            print(f"  ✓ Completed: {sql_file.name}")
        
        cursor.close()
        conn.close()
        
        print(f"  ✓ All SQL files executed successfully\n")
        return True
    
    except Exception as e:
        print(f"  ✗ SQL execution failed: {e}")
        return False


def run_stage(stage: dict) -> bool:
    """Run a single pipeline stage."""
    try:
        # Single script execution
        if 'script' in stage and stage['script']:
            return run_python_script(stage['script'], stage.get('args', []))
        
        # Multiple scripts execution
        elif 'scripts' in stage:
            for script in stage['scripts']:
                if not run_python_script(script):
                    return False
            return True
        
        # SQL file execution
        elif 'sql_files' in stage:
            return run_sql_files(stage['sql_files'])
        
        else:
            print(f"  ⚠  No execution defined for stage")
            return True
    
    except Exception as e:
        print(f"  ✗ Stage execution error: {e}")
        return False


def get_stage_index(stage_name: str) -> Optional[int]:
    """Get index of stage by name."""
    for i, stage in enumerate(STAGES):
        if stage['name'] == stage_name:
            return i
    return None


def main():
    """Main pipeline execution."""
    parser = argparse.ArgumentParser(description='Run data synthesis pipeline')
    parser.add_argument('--stage', help='Run single stage by name')
    parser.add_argument('--from', dest='from_stage', help='Run from stage onwards')
    parser.add_argument('--skip', nargs='+', help='Skip specific stages', default=[])
    parser.add_argument('--dry-run', action='store_true', help='Show stages without executing')
    
    args = parser.parse_args()
    
    print_header("PCC Data Pipeline Orchestrator")
    
    # Determine which stages to run
    start_index = 0
    end_index = len(STAGES)
    
    if args.stage:
        # Single stage mode
        stage_index = get_stage_index(args.stage)
        if stage_index is None:
            print(f"✗ Unknown stage: {args.stage}")
            print(f"\nAvailable stages:")
            for stage in STAGES:
                print(f"  - {stage['name']}: {stage['description']}")
            sys.exit(1)
        
        start_index = stage_index
        end_index = stage_index + 1
        print(f"Running single stage: {args.stage}")
    
    elif args.from_stage:
        # From stage onwards
        stage_index = get_stage_index(args.from_stage)
        if stage_index is None:
            print(f"✗ Unknown stage: {args.from_stage}")
            sys.exit(1)
        
        start_index = stage_index
        print(f"Running from stage: {args.from_stage}")
    
    else:
        print(f"Running all stages")
    
    # Filter stages to run
    stages_to_run = STAGES[start_index:end_index]
    stages_to_run = [s for s in stages_to_run if s['name'] not in args.skip]
    
    print(f"\nPipeline plan ({len(stages_to_run)} stages):")
    for i, stage in enumerate(stages_to_run, 1):
        status = "required" if stage.get('required') else "optional"
        print(f"  {i}. {stage['name']}: {stage['description']} ({status})")
    
    if args.dry_run:
        print(f"\n✓ Dry run complete - no stages executed")
        return
    
    # Execute stages
    print_header("Starting Pipeline Execution")
    
    start_time = time.time()
    failed_stages = []
    
    for i, stage in enumerate(stages_to_run, 1):
        print_stage_header(i, len(stages_to_run), stage['name'], stage['description'])
        
        stage_start = time.time()
        success = run_stage(stage)
        stage_duration = time.time() - stage_start
        
        if success:
            print(f"✓ Stage '{stage['name']}' completed in {stage_duration:.1f}s")
        else:
            print(f"✗ Stage '{stage['name']}' failed after {stage_duration:.1f}s")
            failed_stages.append(stage['name'])
            
            if stage.get('required'):
                print(f"\n✗ Required stage failed - stopping pipeline")
                break
            else:
                print(f"\n⚠  Optional stage failed - continuing pipeline")
    
    # Summary
    total_duration = time.time() - start_time
    
    print_header("Pipeline Execution Summary")
    
    successful_count = len(stages_to_run) - len(failed_stages)
    
    print(f"Completed: {successful_count}/{len(stages_to_run)} stages")
    print(f"Duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    
    if failed_stages:
        print(f"\n✗ Failed stages:")
        for stage in failed_stages:
            print(f"  - {stage}")
        sys.exit(1)
    else:
        print(f"\n✓ All stages completed successfully!")
        print(f"\nNext steps:")
        print(f"  1. Review data quality: python tests/integration/test_data_quality.py")
        print(f"  2. Test analytics queries: python tests/integration/test_sql_queries.py")
        print(f"  3. Verify vector store: Access ChromaDB at http://localhost:8200")
        print(f"  4. Proceed to Phase 2: Agent development")


if __name__ == "__main__":
    main()
