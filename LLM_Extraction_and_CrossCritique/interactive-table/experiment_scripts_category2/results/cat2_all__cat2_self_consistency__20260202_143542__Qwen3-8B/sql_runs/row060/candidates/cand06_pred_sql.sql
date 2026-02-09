with valid PostgreSQL syntax.
- Do not include any other text.

{  
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"cancer_type\" ILIKE '%Non-Small Cell Lung%' AND \"class_of_ici\" IN ('PD1', 'CTLA4') AND \"included_in_ma\" = true;