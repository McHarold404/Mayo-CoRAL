SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"cancer_type\" ILIKE '%Non-Small Cell Lung%' AND \"included_in_ma\" = 'yes' AND \"class_of_ici\" ILIKE '%PD1%' OR \"class_of_ici\" ILIKE '%CTLA-4%'", 
  "answer": "Non-Small Cell Lung studies included in the meta-analysis that used PD1 or CTLA-4 agents are listed with their corresponding details.",
  "assumptions": "Assuming 'included_in_ma' indicates the study is part of a meta-analysis and 'class_of_ici' contains the relevant immune checkpoint inhibitor class."
}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"cancer_type\" ILIKE '%Non-Small Cell Lung%' AND \"included_in_ma\" = 'yes' AND (\"class_of_ici\" ILIKE '%PD1%' OR \"class_of_ici\" ILIKE '%CTLA-4%')",
  "answer": "Non-Small Cell Lung studies included in the meta-analysis that used PD1 or CTLA-4 agents are listed with their corresponding details.",
  "assumptions": "Assuming 'included_in_ma' indicates the study is part of a meta-analysis and 'class_of_ici' contains the relevant immune checkpoint inhibitor class."
}