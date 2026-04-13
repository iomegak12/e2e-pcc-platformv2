# Clinical Guidelines Registry

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
