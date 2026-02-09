with valid PostgreSQL syntax.
- No markdown, no extra text.

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"class_of_ici\" = 'PD1' OR \"class_of_ici\" = 'CTLA4' AND \"priamry_multiple_composite_or_co_primary_endpoints\" ILIKE '%yes%'",
  "answer": "PD1 and CTLA-4 trials that reported composite or co-primary endpoints are listed.",
  "assumptions": ""
}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE (\"class_of_ici\" = 'PD1' OR \"class_of_ici\" = 'CTLA4') AND \"priamry_multiple_composite_or_co_primary_endpoints\" ILIKE '%yes%'",
  "answer": "PD1 and CTLA-4 trials that reported composite or co-primary endpoints are listed.",
  "assumptions": "Assumed 'priamry_multiple_composite_or_co_primary_endpoints' contains 'yes' when composite/co-primary endpoints are reported."
}