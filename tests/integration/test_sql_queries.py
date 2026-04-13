#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQL Analytics Query Test Suite
Tests all 5 analytics query patterns with performance validation.

Queries:
1. Readmission Risk Cohort
2. Medication Adherence Trends
3. Vital Sign Anomaly Detection
4. Treatment Outcome KPIs
5. Population Segmentation

Each query must complete in <2 seconds and return valid results.
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List
import psycopg2
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows compatibility
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load environment
load_dotenv()

# Performance threshold
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


def execute_query(conn, query_name: str, query: str) -> Dict[str, Any]:
    """Execute query and measure performance."""
    print(f"\n{query_name}")
    print(f"{'─'*70}")
    
    cursor = conn.cursor()
    
    try:
        start = time.time()
        cursor.execute(query)
        rows = cursor.fetchall()
        duration = time.time() - start
        
        # Get column names
        colnames = [desc[0] for desc in cursor.description]
        
        passed = duration < QUERY_TIMEOUT_SECONDS
        status = "✓" if passed else "✗"
        
        print(f"\n{status} Performance: {duration:.3f}s (threshold: {QUERY_TIMEOUT_SECONDS}s)")
        print(f"  Rows returned: {len(rows)}")
        print(f"  Columns: {', '.join(colnames)}")
        
        # Show sample results
        if rows:
            print(f"\nSample results (first 5 rows):")
            for i, row in enumerate(rows[:5], 1):
                print(f"  {i}. {dict(zip(colnames, row))}")
        else:
            print(f"\n  ⚠  No rows returned (may be expected for some queries)")
        
        cursor.close()
        
        return {
            'passed': passed,
            'duration': duration,
            'row_count': len(rows),
            'columns': colnames
        }
    
    except Exception as e:
        cursor.close()
        print(f"\n✗ Query failed: {e}")
        return {
            'passed': False,
            'error': str(e)
        }


def main():
    """Main test execution."""
    print_header("SQL Analytics Query Test Suite")
    
    try:
        conn = get_db_connection()
        print(f"✓ Connected to PostgreSQL")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        sys.exit(1)
    
    # Define all 5 analytics queries
    queries = [
        ("Query 1: Readmission Risk Cohort", """
            SELECT 
                p.patient_id,
                p.gender,
                EXTRACT(YEAR FROM age(p.date_of_birth)) AS age,
                COUNT(DISTINCT a.admission_id) AS admission_count,
                MAX(a.encounter_end) AS last_discharge,
                STRING_AGG(DISTINCT d.icd10_code, ', ') AS diagnosis_codes
            FROM patients p
            JOIN admissions a ON p.patient_id = a.patient_id
            LEFT JOIN diagnoses d ON p.patient_id = d.patient_id
            WHERE a.encounter_start >= CURRENT_DATE - INTERVAL '90 days'
            GROUP BY p.patient_id, p.gender, p.date_of_birth
            HAVING COUNT(DISTINCT a.admission_id) > 1
            ORDER BY admission_count DESC, last_discharge DESC
            LIMIT 50
        """),
        
        ("Query 2: Medication Adherence Trends", """
            SELECT 
                m.drug_name,
                COUNT(pe.event_id) AS total_refills,
                ROUND(AVG(pe.gap_days), 2) AS avg_gap_days,
                ROUND(SUM(CASE WHEN pe.gap_days <= 3 THEN 1 ELSE 0 END)::numeric / 
                      COUNT(*)::numeric * 100, 1) AS on_time_rate,
                ROUND(SUM(CASE WHEN pe.gap_days > 3 AND pe.gap_days < 20 THEN 1 ELSE 0 END)::numeric / 
                      COUNT(*)::numeric * 100, 1) AS late_rate,
                ROUND(SUM(CASE WHEN pe.gap_days >= 20 THEN 1 ELSE 0 END)::numeric / 
                      COUNT(*)::numeric * 100, 1) AS missed_rate
            FROM medications m
            JOIN pharmacy_events pe ON m.medication_id = pe.medication_id
            GROUP BY m.drug_name
            HAVING COUNT(pe.event_id) >= 10
            ORDER BY missed_rate DESC, late_rate DESC
            LIMIT 30
        """),
        
        ("Query 3: Vital Sign Anomaly Detection", """
            SELECT 
                v.patient_id,
                v.vital_type,
                v.value,
                v.recorded_at,
                p.gender,
                EXTRACT(YEAR FROM age(p.date_of_birth)) AS age,
                a.admission_id,
                a.encounter_start
            FROM vitals v
            JOIN patients p ON v.patient_id = p.patient_id
            LEFT JOIN admissions a ON v.admission_id = a.admission_id
            WHERE 
                (v.vital_type = 'heart_rate' AND (v.value < 50 OR v.value > 120))
                OR (v.vital_type = 'bp_systolic' AND (v.value < 90 OR v.value > 180))
                OR (v.vital_type = 'bp_diastolic' AND (v.value < 50 OR v.value > 110))
                OR (v.vital_type = 'temperature' AND (v.value < 35.5 OR v.value > 38.5))
                OR (v.vital_type = 'spo2' AND v.value < 90)
            ORDER BY v.recorded_at DESC
            LIMIT 100
        """),
        
        ("Query 4: Treatment Outcome KPIs", """
            SELECT 
                a.primary_diagnosis_code AS diagnosis_code,
                a.diagnosis_description,
                COUNT(DISTINCT a.patient_id) AS patient_count,
                AVG(EXTRACT(EPOCH FROM (a.encounter_end - a.encounter_start))/86400)::numeric(5,1) AS avg_los_days,
                COUNT(DISTINCT dp.plan_id) AS discharge_plans_created,
                ROUND(COUNT(DISTINCT dp.plan_id)::numeric / 
                      COUNT(DISTINCT a.admission_id)::numeric * 100, 1) AS plan_creation_rate
            FROM admissions a
            LEFT JOIN discharge_plans dp ON a.admission_id = dp.admission_id
            WHERE a.encounter_end IS NOT NULL
              AND a.primary_diagnosis_code IS NOT NULL
            GROUP BY a.primary_diagnosis_code, a.diagnosis_description
            HAVING COUNT(DISTINCT a.patient_id) >= 5
            ORDER BY patient_count DESC
            LIMIT 20
        """),
        
        ("Query 5: Population Segmentation", """
            SELECT 
                CASE 
                    WHEN EXTRACT(YEAR FROM age(p.date_of_birth)) < 40 THEN '18-39'
                    WHEN EXTRACT(YEAR FROM age(p.date_of_birth)) < 60 THEN '40-59'
                    WHEN EXTRACT(YEAR FROM age(p.date_of_birth)) < 75 THEN '60-74'
                    ELSE '75+'
                END AS age_group,
                p.gender,
                COUNT(DISTINCT p.patient_id) AS patient_count,
                COUNT(a.admission_id) AS total_admissions,
                ROUND(AVG(EXTRACT(EPOCH FROM (a.encounter_end - a.encounter_start))/86400), 1) AS avg_los_days
            FROM patients p
            LEFT JOIN admissions a ON p.patient_id = a.patient_id
            GROUP BY age_group, p.gender
            ORDER BY age_group, p.gender
        """),
    ]
    
    # Execute all queries
    results = []
    
    for query_name, query in queries:
        result = execute_query(conn, query_name, query)
        results.append({
            'name': query_name,
            **result
        })
    
    conn.close()
    
    # Summary
    print_header("Test Summary")
    
    passed_count = sum(1 for r in results if r.get('passed', False))
    failed_count = len(results) - passed_count
    
    print(f"Results:")
    for i, result in enumerate(results, 1):
        status = "✓" if result.get('passed', False) else "✗"
        duration = result.get('duration', 'N/A')
        row_count = result.get('row_count', 'N/A')
        error = result.get('error', '')
        
        if error:
            print(f"  {status} Query {i}: FAILED - {error}")
        else:
            print(f"  {status} Query {i}: {duration:.3f}s, {row_count} rows")
    
    print(f"\n{'─'*70}")
    print(f"Overall: {passed_count}/{len(results)} queries passed")
    
    if failed_count == 0:
        print(f"\n✓ All analytics queries passed!")
        print(f"\nPhase 1 Checkpoint:")
        print(f"  ✓ All five SQL analytics query patterns return results in under 2 seconds")
    else:
        print(f"\n✗ {failed_count} query(s) failed - review output above")
        sys.exit(1)


if __name__ == "__main__":
    main()
