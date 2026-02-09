with double quotes.
- Do NOT assume any columns not listed.
- Do NOT use backticks or other formatting.

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"name_of_ici\" = 'CTLA-4' AND \"priamry_multiple_composite_or_co_primary_endpoints\"::text ILIKE '%composite%' OR \"priamry_multiple_composite_or_co_primary_endpoints\"::text ILIKE '%co-primary%';