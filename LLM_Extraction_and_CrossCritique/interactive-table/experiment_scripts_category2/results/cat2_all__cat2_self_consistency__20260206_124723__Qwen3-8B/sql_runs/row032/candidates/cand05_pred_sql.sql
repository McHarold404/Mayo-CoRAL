SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"class_of_ici\", \"priamry_multiple_composite_or_co_primary_endpoints\" FROM public.\"clinical_trials\" WHERE \"class_of_ici\" ILIKE '%PD1%' OR \"class_of_ici\" ILIKE '%CTLA-4%' AND \"priamry_multiple_composite_or_co_primary_endpoints\" IS NOT NULL",
  "answer": "The query retrieves PD1 and CTLA-4 trials with composite or co-primary endpoints.",
  "assumptions": "Assumes that 'PD1' and 'CTLA-4' are correctly mapped in the 'class_of_ici' column and that 'priamry_multiple_composite_or_co_primary_endpoints' indicates composite endpoints."
}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"class_of_ici\", \"priamry_multiple_composite_or_co_primary_endpoints\" FROM public.\"clinical_trials\" WHERE (\"class_of_ici\" ILIKE '%PD1%' OR \"class_of_ici\" ILIKE '%CTLA-4%') AND \"priamry_multiple_composite_or_co_primary_endpoints\" IS NOT NULL",
  "answer": "The query retrieves PD1 and CTLA-4 trials that reported composite or co-primary endpoints.",
  "assumptions": "Assumes 'PD1' is correctly mapped in the 'class_of_ici' column and that 'priamry_multiple_composite_or_co_primary_endpoints' indicates composite endpoints."
}