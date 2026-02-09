SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"cancer_type\" = 'Non-Small Cell Lung' AND \"included_in_ma\" = true AND (\"class_of_ici\" ILIKE '%PD1%' OR \"class_of_ici\" ILIKE '%CTLA-4%')",
  "answer": "The query retrieves Non-Small Cell Lung studies included in the meta-analysis that used PD1 or CTLA-4 agents.",
  "assumptions": ""
}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"cancer_type\" = 'Non-Small Cell Lung' AND \"included_in_ma\" = true AND (\"class_of_ici\" ILIKE '%PD1%' OR \"class_of_ici\" ILIKE '%CTLA-4%')",
  "answer": "The query retrieves Non-Small Cell Lung studies included in the meta-analysis that used PD1 or CTLA-4 agents.",
  "assumptions": ""
}