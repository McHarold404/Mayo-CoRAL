with double quotes.
- Use the exact value for "class_of_ici" when PD-1 is mentioned (no dash).

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"treatment_regimen\", \"class_of_ici\", \"name_of_ici\", \"monotherapy_combination\" FROM public.\"clinical_trials\" WHERE \"trial_phase\" = 'Phase 2' AND \"cancer_type\" = 'Breast' AND \"class_of_ici\" = 'PD1' AND \"type_of_combination\" = 'monotherapy' AND \"is_pd_l1_positivity_inclusion_criteria\" = 'Yes' AND \"type_of_therapy\" = 'immunotherapy' AND \"number_of_arms\" = 1",
  "answer": "Phase 2 PD-L1 monotherapy trials in Breast are available, with their regimens listed in the treatment_regimen column.",
  "assumptions": "Assumed that 'PD-1' is mapped to 'PD1' in the class_of_ici column and that 'monotherapy' is indicated by 'monotherapy_combination' and 'type_of_combination' fields."
}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"treatment_regimen\", \"class_of_ici\", \"name_of_ici\", \"monotherapy_combination\" FROM public.\"clinical_trials\" WHERE \"trial_phase\" = 'Phase 2' AND \"cancer_type\" = 'Breast' AND \"class_of_ici\" = 'PD1' AND \"type_of_combination\" = 'monotherapy' AND \"is_pd_l1_positivity_inclusion_criteria\" = 'Yes' AND \"type_of_therapy\" = 'immunotherapy' AND \"number_of_arms\" = 1",
  "answer": "Phase 2 PD-L1 monotherapy trials in Breast are available, with their regimens listed in the treatment_regimen column.",
  "assumptions": "Assumed that 'PD-1' is mapped to 'PD1' in the class_of_ici column and that 'monotherapy' is indicated by 'monotherapy_combination' and 'type_of_combination' fields."
}