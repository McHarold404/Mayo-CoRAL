SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"trial_phase\", \"trial_name\", \"cancer_type\", \"treatment_regimen\", \"name_of_ici\", \"class_of_ici\", \"type_of_combination\", \"control_regimen\" FROM public.\"clinical_trials\" WHERE \"trial_phase\" = 'Phase 3' AND \"cancer_type\" = 'Non-Small Cell Lung' AND \"class_of_ici\" = 'PD1' AND \"name_of_ici\" ILIKE '%PDL1%' AND \"name_of_ici\" ILIKE '%CTLA4%'",
  "answer": "Phase 3 PD-L1, CTLA-4 combination trials in Non-Small Cell Lung include [trial names], with regimens [regimen details].",
  "assumptions": "Assuming 'PD-L1' is mapped to 'PD1' in the class_of_ici column and that the combination includes both PD-L1 and CTLA-4 agents."
}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"trial_phase\", \"trial_name\", \"cancer_type\", \"treatment_regimen\", \"name_of_ici\", \"class_of_ici\", \"type_of_combination\", \"control_regimen\" FROM public.\"clinical_trials\" WHERE \"trial_phase\" = 'Phase 3' AND \"cancer_type\" = 'Non-Small Cell Lung' AND \"class_of_ici\" = 'PD1' AND \"name_of_ici\" ILIKE '%PDL1%' AND \"name_of_ici\" ILIKE '%CTLA4%'",
  "answer": "Phase 3 PD-L1, CTLA-4 combination trials in Non-Small Cell Lung include specific trials with regimens involving PD-L1 and CTLA-4 inhibitors.",
  "assumptions": "Assuming 'PD-L1' is mapped to 'PD1' in the class_of_ici column and that the combination includes both PD-L1 and CTLA-4 agents."
}