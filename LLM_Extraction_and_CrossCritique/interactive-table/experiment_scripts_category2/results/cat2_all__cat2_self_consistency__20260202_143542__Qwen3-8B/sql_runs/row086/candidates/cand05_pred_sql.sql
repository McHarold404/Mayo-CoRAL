with double quotes.
- Do NOT include any other text.

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"trial_name\", \"trial_phase\", \"treatment_regimen\", \"name_of_ici\", \"class_of_ici\", \"cancer_type\" FROM public.\"clinical_trials\" WHERE \"trial_phase\" = 'Phase 3' AND \"cancer_type\" = 'Colorectal' AND \"class_of_ici\" = 'PD1' AND \"type_of_combination\" = 'monotherapy' AND \"type_of_therapy\" = 'PD-L1 inhibitor'",
  "answer": "Phase 3 PD-L1 monotherapy trials in Colorectal are available, with regimens detailed in the results.",
  "assumptions": "Assumed 'PD-L1' is mapped to 'PD1' in 'class_of_ici' and 'type_of_therapy' refers to PD-L1 inhibitor."
}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"trial_name\", \"trial_phase\", \"treatment_regimen\", \"name_of_ici\", \"class_of_ici\", \"cancer_type\" FROM public.\"clinical_trials\" WHERE \"trial_phase\" = 'Phase 3' AND \"cancer_type\" = 'Colorectal' AND \"class_of_ici\" = 'PD1' AND \"type_of_combination\" = 'monotherapy' AND \"type_of_therapy\" = 'PD-L1 inhibitor'",
  "answer": "Phase 3 PD-L1 monotherapy trials in Colorectal are available, with regimens detailed in the results.",
  "assumptions": "Assumed 'PD-L1' is mapped to 'PD1' in 'class_of_ici' and 'type_of_therapy' refers to PD-L1 inhibitor."
}