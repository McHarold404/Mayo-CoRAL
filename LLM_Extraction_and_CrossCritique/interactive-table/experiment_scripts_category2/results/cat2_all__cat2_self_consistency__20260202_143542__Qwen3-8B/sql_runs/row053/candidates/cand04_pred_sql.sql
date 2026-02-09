SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"class_of_ici\" = 'PD1' AND \"priamry_multiple_composite_or_co_primary_endpoints\" = 'Yes'",
  "answer": "PD-L1 trials that reported composite or co-primary endpoints are listed with their NCT, author, year, and PubMed ID.",
  "assumptions": "Assuming 'PD1' is the correct mapping for PD-L1 in the class_of_ici column and that 'Yes' indicates the presence of composite or co-primary endpoints."
}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"class_of_ici\" = 'PD1' AND \"priamry_multiple_composite_or_co_primary_endpoints\" = 'Yes'",
  "answer": "PD-L1 trials that reported composite or co-primary endpoints are listed with their NCT, author, year, and PubMed ID.",
  "assumptions": "Assuming 'PD1' is the correct mapping for PD-L1 in the class_of_ici column and that 'Yes' indicates the presence of composite or co-primary endpoints."
}