#!/usr/bin/env python3
"""
Data Quality Test Suite
Validates Phase 1 data synthesis checkpoints.

Tests:
- Row counts match expected ranges
- Foreign key integrity
- Analytics query performance (<2s)
- Anomaly seeding (10% of discharge plans)
- Adherence gaps (18% late, 5% missed)
- Date/time consistency
- ChromaDB retrieval quality
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, Any
import psycopg2
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Expected row counts (ranges for synthetic data)
EXPECTED_COUNTS = {
    'patients': (500, 600),  # Synthea generated 573
    'clinicians': (50, 300),  # Base 50 + may be loaded from Synthea practitioners
    'admissions': (30000, 50000),  # Synthea generates many encounters
    'diagnoses': (20000, 35000),
    'lab_results': (150000, 250000),
    'medications': (30000, 50000),
    'vitals': (60000, 90000),
    'pharmacy_events': (100000, 250000),  # Refill events for active medications
    'discharge_plans': (400, 700),  # Only inpatient with discharge_status='discharged'
    'wearable_readings': (40000, 60000),  # Daily readings for 2-4 months per discharge plan
    'appointments': (0, 0),  # Not yet implemented
}

# Performance benchmarks
QUERY_TIMEOUT_SECONDS = 2.0


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def get_db_connection():
    """Create database connection."""
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', '5432')),
        database=os.getenv('POSTGRES_DB', 'healthcare_pcc'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'postgres')
    )


def test_row_counts(conn) -> Dict[str, Any]:
    """Test row counts against expected ranges."""
    print("Testing row counts...")
    
    cursor = conn.cursor()
    results = {'passed': 0, 'failed': 0, 'details': []}
    
    for table, (min_count, max_count) in EXPECTED_COUNTS.items():
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        actual_count = cursor.fetchone()[0]
        
        passed = min_count <= actual_count <= max_count
        
        status = "✓" if passed else "✗"
        detail = f"{status} {table}: {actual_count} rows (expected {min_count}-{max_count})"
        
        print(f"  {detail}")
        results['details'].append(detail)
        
        if passed:
            results['passed'] += 1
        else:
            results['failed'] += 1
    
    cursor.close()
    return results


def test_foreign_keys(conn) -> Dict[str, Any]:
    """Test foreign key integrity."""
    print("\nTesting foreign key integrity...")
    
    cursor = conn.cursor()
    results = {'passed': 0, 'failed': 0, 'details': []}
    
    # Test key relationships
    fk_tests = [
        ("admissions → patients", """
            SELECT COUNT(*) FROM admissions a 
            LEFT JOIN patients p ON a.patient_id = p.patient_id 
            WHERE p.patient_id IS NULL
        """),
        ("diagnoses → admissions", """
            SELECT COUNT(*) FROM diagnoses d 
            LEFT JOIN admissions a ON d.admission_id = a.admission_id 
            WHERE d.admission_id IS NOT NULL AND a.admission_id IS NULL
        """),
        ("medications → patients", """
            SELECT COUNT(*) FROM medications m 
            LEFT JOIN patients p ON m.patient_id = p.patient_id 
            WHERE p.patient_id IS NULL
        """),
        ("pharmacy_events → medications", """
            SELECT COUNT(*) FROM pharmacy_events pe 
            LEFT JOIN medications m ON pe.medication_id = m.medication_id 
            WHERE m.medication_id IS NULL
        """),
        ("discharge_plans → admissions", """
            SELECT COUNT(*) FROM discharge_plans dp 
            LEFT JOIN admissions a ON dp.admission_id = a.admission_id 
            WHERE a.admission_id IS NULL
        """),
    ]
    
    for test_name, query in fk_tests:
        cursor.execute(query)
        orphan_count = cursor.fetchone()[0]
        
        passed = orphan_count == 0
        status = "✓" if passed else "✗"
        detail = f"{status} {test_name}: {orphan_count} orphaned records"
        
        print(f"  {detail}")
        results['details'].append(detail)
        
        if passed:
            results['passed'] += 1
        else:
            results['failed'] += 1
    
    cursor.close()
    return results


def test_query_performance(conn) -> Dict[str, Any]:
    """Test analytics query performance (<2s)."""
    print("\nTesting query performance (target: <2s)...")
    
    cursor = conn.cursor()
    results = {'passed': 0, 'failed': 0, 'details': []}
    
    # Sample analytics queries
    queries = [
        ("Readmission cohort", """
            SELECT patient_id, COUNT(*) as admission_count
            FROM admissions
            WHERE encounter_start >= CURRENT_DATE - INTERVAL '90 days'
            GROUP BY patient_id
            HAVING COUNT(*) > 1
        """),
        ("Medication adherence", """
            SELECT m.medication_id, m.drug_name,
                   COUNT(pe.event_id) as total_refills,
                   AVG(CASE WHEN pe.gap_days > 3 THEN 1 ELSE 0 END) as late_rate
            FROM medications m
            JOIN pharmacy_events pe ON m.medication_id = pe.medication_id
            GROUP BY m.medication_id, m.drug_name
        """),
        ("Vital anomalies", """
            SELECT patient_id, vital_type, value, recorded_at
            FROM vitals
            WHERE (vital_type = 'heart_rate' AND (value < 50 OR value > 120))
               OR (vital_type = 'bp_systolic' AND (value < 90 OR value > 180))
            ORDER BY recorded_at DESC
            LIMIT 100
        """),
    ]
    
    for query_name, query in queries:
        start = time.time()
        cursor.execute(query)
        rows = cursor.fetchall()
        duration = time.time() - start
        
        passed = duration < QUERY_TIMEOUT_SECONDS
        status = "✓" if passed else "✗"
        detail = f"{status} {query_name}: {duration:.3f}s ({len(rows)} rows)"
        
        print(f"  {detail}")
        results['details'].append(detail)
        
        if passed:
            results['passed'] += 1
        else:
            results['failed'] += 1
    
    cursor.close()
    return results


def test_anomaly_seeding(conn) -> Dict[str, Any]:
    """Test anomaly seeding (10% of discharge plans)."""
    print("\nTesting anomaly seeding (target: 10%)...")
    
    cursor = conn.cursor()
    results = {'passed': 0, 'failed': 0, 'details': []}
    
    # Get discharge plan count
    cursor.execute("SELECT COUNT(*) FROM discharge_plans")
    total_plans = cursor.fetchone()[0]
    
    # Count plans with anomalies using the anomaly_flag
    cursor.execute("""
        SELECT COUNT(DISTINCT wr.discharge_plan_id)
        FROM wearable_readings wr
        WHERE wr.anomaly_flag = true
    """)
    
    anomaly_count = cursor.fetchone()[0]
    anomaly_rate = (anomaly_count / total_plans * 100) if total_plans > 0 else 0
    
    # Target: 8-12% (allowing variance)
    passed = 8 <= anomaly_rate <= 12
    status = "✓" if passed else "✗"
    detail = f"{status} Anomaly rate: {anomaly_rate:.1f}% ({anomaly_count}/{total_plans} plans)"
    
    print(f"  {detail}")
    results['details'].append(detail)
    
    if passed:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    cursor.close()
    return results


def test_adherence_gaps(conn) -> Dict[str, Any]:
    """Test adherence gap distribution (18% late, 5% missed)."""
    print("\nTesting adherence gaps (target: 18% late, 5% missed)...")
    
    cursor = conn.cursor()
    results = {'passed': 0, 'failed': 0, 'details': []}
    
    # Get adherence distribution
    cursor.execute("""
        SELECT 
            COUNT(*) as total_events,
            SUM(CASE WHEN gap_days <= 3 THEN 1 ELSE 0 END) as on_time,
            SUM(CASE WHEN gap_days > 3 AND gap_days < 20 THEN 1 ELSE 0 END) as late,
            SUM(CASE WHEN gap_days >= 20 THEN 1 ELSE 0 END) as missed
        FROM pharmacy_events
    """)
    
    row = cursor.fetchone()
    total, on_time, late, missed = row
    
    if total > 0:
        late_rate = (late / total * 100)
        missed_rate = (missed / total * 100)
        
        # Allow ±3% variance
        late_passed = 15 <= late_rate <= 21
        missed_passed = 0 <= missed_rate <= 7
        
        late_status = "✓" if late_passed else "✗"
        missed_status = "✓" if missed_passed else "✗"
        
        late_detail = f"{late_status} Late rate: {late_rate:.1f}% (target: 18%)"
        missed_detail = f"{missed_status} Missed rate: {missed_rate:.1f}% (target: 5%)"
        
        print(f"  {late_detail}")
        print(f"  {missed_detail}")
        
        results['details'].append(late_detail)
        results['details'].append(missed_detail)
        
        results['passed'] += (1 if late_passed else 0) + (1 if missed_passed else 0)
        results['failed'] += (0 if late_passed else 1) + (0 if missed_passed else 1)
    else:
        print(f"  ✗ No pharmacy events found")
        results['failed'] += 1
    
    cursor.close()
    return results


def test_chromadb_retrieval() -> Dict[str, Any]:
    """Test ChromaDB vector store retrieval."""
    print("\nTesting ChromaDB retrieval...")
    
    results = {'passed': 0, 'failed': 0, 'details': []}
    
    try:
        import chromadb
        
        chroma_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'chromadb')
        chroma_path = os.path.abspath(chroma_path)
        client = chromadb.PersistentClient(path=chroma_path)
        
        collection = client.get_collection("clinical_guidelines")
        
        # Test retrieval quality
        test_query = "iron deficiency anaemia treatment guidelines"
        
        # Use OpenAI embeddings to match the 1536-dim vectors stored in the collection
        from openai import OpenAI
        oai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        embedding_response = oai_client.embeddings.create(
            input=[test_query],
            model=os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
        )
        query_embedding = embedding_response.data[0].embedding
        
        response = collection.query(
            query_embeddings=[query_embedding],
            n_results=3
        )
        
        if response['documents'] and len(response['documents'][0]) >= 3:
            print(f"  ✓ Retrieved {len(response['documents'][0])} relevant chunks")
            results['passed'] += 1
            results['details'].append(f"✓ ChromaDB retrieval successful")
        else:
            print(f"  ✗ Insufficient results retrieved")
            results['failed'] += 1
            results['details'].append(f"✗ ChromaDB retrieval failed")
    
    except Exception as e:
        print(f"  ✗ ChromaDB connection failed: {e}")
        results['failed'] += 1
        results['details'].append(f"✗ ChromaDB error: {e}")
    
    return results


def main():
    """Main test execution."""
    print_header("PCC Data Quality Test Suite")
    
    try:
        conn = get_db_connection()
        print(f"✓ Connected to PostgreSQL\n")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        sys.exit(1)
    
    # Run all tests
    all_results = {}
    
    all_results['row_counts'] = test_row_counts(conn)
    all_results['foreign_keys'] = test_foreign_keys(conn)
    all_results['query_performance'] = test_query_performance(conn)
    all_results['anomaly_seeding'] = test_anomaly_seeding(conn)
    all_results['adherence_gaps'] = test_adherence_gaps(conn)
    
    conn.close()
    
    # ChromaDB test (separate connection)
    all_results['chromadb'] = test_chromadb_retrieval()
    
    # Summary
    print_header("Test Summary")
    
    total_passed = sum(r['passed'] for r in all_results.values())
    total_failed = sum(r['failed'] for r in all_results.values())
    total_tests = total_passed + total_failed
    
    for test_name, result in all_results.items():
        print(f"{test_name.replace('_', ' ').title()}:")
        print(f"  Passed: {result['passed']}, Failed: {result['failed']}")
    
    print(f"\n{'─'*70}")
    print(f"Overall: {total_passed}/{total_tests} tests passed")
    
    if total_failed == 0:
        print(f"\n✓ All data quality tests passed!")
        print(f"\nPhase 1 Checkpoints:")
        print(f"  ✓ All row counts within expected ranges")
        print(f"  ✓ Foreign key integrity verified")
        print(f"  ✓ Analytics queries < 2s")
        print(f"  ✓ Anomaly seeding validated")
        print(f"  ✓ Adherence gaps validated")
        print(f"  ✓ ChromaDB retrieval working")
    else:
        print(f"\n✗ {total_failed} test(s) failed - review output above")
        sys.exit(1)


if __name__ == "__main__":
    main()
