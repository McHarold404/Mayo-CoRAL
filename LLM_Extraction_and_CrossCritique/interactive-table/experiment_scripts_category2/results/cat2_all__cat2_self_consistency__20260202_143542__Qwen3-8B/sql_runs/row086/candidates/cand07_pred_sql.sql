SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"trial_phase\", \"treatment_regimen\", \"name_of_ici\", \"class_of_ici\", \"cancer_type\" FROM public.\"clinical_trials\" WHERE \"trial_phase\" = 'Phase 3' AND \"cancer_type\" = 'Colorectal' AND \"class_of_ici\" = 'PD1' AND \"type_of_combination\" = 'Monotherapy' AND \"type_of_combination_1\" = 'Monotherapy' AND \"type_of_therapy\" = 'Immunotherapy'","answer":"Phase 3 PD-L1 monotherapy trials in Colorectal are listed with their regimens.","assumptions":"Assumed that 'PD-L1' is mapped to 'PD1' in the class_of_ici column and that 'type_of_combination' and 'type_of_combination_1' both indicate monotherapy."}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"trial_phase\", \"treatment_regimen\", \"name_of_ici\", \"class_of_ici\", \"cancer_type\" FROM public.\"clinical_trials\" WHERE \"trial_phase\" = 'Phase 3' AND \"cancer_type\" = 'Colorectal' AND \"class_of_ici\" = 'PD1' AND \"monotherapy_combination\" = 'Yes' AND \"type_of_therapy\" = 'Immunotherapy'",
  "answer": "Phase 3 PD-L1 monotherapy trials in Colorectal are listed with their regimens.",
  "assumptions": "Assumed that 'PD-L1' is mapped to 'PD1' in the class_of_ici column and that 'monotherapy_combination' indicates monotherapy use."
}