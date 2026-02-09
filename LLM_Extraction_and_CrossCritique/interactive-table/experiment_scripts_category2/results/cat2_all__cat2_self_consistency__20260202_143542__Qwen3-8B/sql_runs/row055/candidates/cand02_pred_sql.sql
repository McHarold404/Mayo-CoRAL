SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"class_of_ici\" ILIKE '%pd-l1%' AND \"priamry_multiple_composite_or_co_primary_endpoints\"::text ILIKE '%yes%'",
  "answer": "PD-L1 trials that reported composite or co-primary endpoints are listed with their NCT, author, year, and PubMed ID.",
  "assumptions": "Assumed that 'PD-L1' is mentioned in the 'class_of_ici' field and 'yes' indicates composite or co-primary endpoints in 'priamry_multiple_composite_or_co_primary_endpoints'."
}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"class_of_ici\" ILIKE '%PD1%' AND \"priamry_multiple_composite_or_co_primary_endpoints\"::text ILIKE '%yes%'",
  "answer": "PD-L1 trials that reported composite or co-primary endpoints are listed with their NCT, author, year, and PubMed ID.",
  "assumptions": "Assumed that 'PD-L1' is mapped to 'PD1' in the 'class_of_ici' field and 'yes' indicates composite or co-primary endpoints in 'priamry_multiple_composite_or_co_primary_endpoints'."
}