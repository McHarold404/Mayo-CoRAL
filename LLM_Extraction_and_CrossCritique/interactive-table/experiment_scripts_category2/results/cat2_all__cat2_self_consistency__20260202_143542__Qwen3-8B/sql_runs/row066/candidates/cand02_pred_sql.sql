with <= 1–2 sentences.
- Assumptions must be a string with <= 1–2 sentences (empty if none).

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"primary_endpoint\" FROM public.\"clinical_trials\" WHERE \"cancer_type\" ILIKE '%melanoma%' AND \"type_of_combination\" ILIKE '%ICI+ICI%'",
  "answer": "The query retrieves Melanoma studies that tested ICI+ICI combinations along with their primary endpoints.",
  "assumptions": "Assumes that 'type_of_combination' field contains entries like 'ICI+ICI' to identify combination therapies."
}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"primary_endpoint\" FROM public.\"clinical_trials\" WHERE \"cancer_type\" ILIKE '%melanoma%' AND \"type_of_combination\" ILIKE '%ICI+ICI%'",
  "answer": "The query retrieves Melanoma studies that tested ICI+ICI combinations along with their primary endpoints.",
  "assumptions": "Assumes that 'type_of_combination' field contains entries like 'ICI+ICI' to identify combination therapies."
}