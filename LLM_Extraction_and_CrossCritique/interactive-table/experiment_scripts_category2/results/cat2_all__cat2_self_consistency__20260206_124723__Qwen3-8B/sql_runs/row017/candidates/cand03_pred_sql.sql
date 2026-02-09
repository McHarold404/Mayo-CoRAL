SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"trial_phase\" = 'Phase 3' AND \"cancer_type\" = 'Small Cell Lung' AND \"class_of_ici\" IS NOT NULL AND \"control_regimen\" ILIKE '%Chemotherapy%'",
  "answer": "The following Small Cell Lung phase 3 trials compared ICI to Chemo: [list of trials].",
  "assumptions": "Assumed that 'Chemo' refers to chemotherapy and that 'ICI' is indicated by non-null 'class_of_ici'."
}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"trial_phase\" = 'Phase 3' AND \"cancer_type\" = 'Small Cell Lung' AND \"class_of_ici\" IS NOT NULL AND \"control_regimen\" ILIKE '%Chemotherapy%'",
  "answer": "The following Small Cell Lung phase 3 trials compared ICI to Chemo: [list of trials].",
  "assumptions": "Assumed that 'Chemo' refers to chemotherapy and that 'ICI' is indicated by non-null 'class_of_ici'."
}