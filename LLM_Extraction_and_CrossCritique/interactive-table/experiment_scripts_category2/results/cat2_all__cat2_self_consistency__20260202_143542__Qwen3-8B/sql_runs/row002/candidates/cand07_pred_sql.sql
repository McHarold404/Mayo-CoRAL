SELECT statement.
- Answer must be <= 1–2 sentences.
- Assumptions must be a string (empty if none).

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"cancer_type\" ILIKE '%melanoma%' AND NOT \"is_pd_l1_positivity_inclusion_criteria\" AND \"is_any_other_biomarker_used_for_inclusion_criteria\" IS TRUE;