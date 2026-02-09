SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"cancer_type\" ILIKE '%Non-Small Cell Lung%' AND \"included_in_ma\" = 't' AND (\"class_of_ici\" ILIKE '%PD1%' OR \"class_of_ici\" ILIKE '%CTLA-4%')",
  "answer": "Non-Small Cell Lung studies included in the meta-analysis that used PD1 or CTLA-4 agents are listed.",
  "assumptions": "Assumed that 'PD1' refers to PD-1 agents and 'CTLA-4' is a class of immunotherapy."
}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"cancer_type\" ILIKE '%Non-Small Cell Lung%' AND \"included_in_ma\" = 't' AND (\"class_of_ici\" ILIKE '%PD1%' OR \"class_of_ici\" ILIKE '%CTLA-4%')",
  "answer": "Non-Small Cell Lung studies included in the meta-analysis that used PD1 or CTLA-4 agents are listed.",
  "assumptions": "Assumed that 'PD1' refers to PD-1 agents and 'CTLA-4' is a class of immunotherapy."
}