SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"trial_phase\", \"cancer_type\", \"treatment_regimen\", \"monotherapy_combination\", \"type_of_combination\", \"control_regimen\", \"type_of_control\", \"primary_endpoint\", \"secondary_endpoint\", \"follow_up_duration_for_primary_endpoint_s_in_months_overall\" FROM public.\"clinical_trials\" WHERE \"trial_phase\" = 'Phase 2' AND \"cancer_type\" = 'Pancreatic' AND \"class_of_ici\" = 'CTLA4' AND \"type_of_combination\" IS NOT NULL AND \"type_of_combination\" != '' AND \"type_of_combination\" != 'monotherapy' AND \"type_of_combination\" != 'combination'",  
  "answer": "Phase 2 CTLA-4 combination trials in Pancreatic cancer are available, with varying regimens and control regimens. Review the listed trials for detailed regimen information.",  
  "assumptions": "Assuming 'CTLA-4' is mapped to 'CTLA4' in the 'class_of_ici' column and that 'type_of_combination' indicates combination therapy."
}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"trial_phase\", \"cancer_type\", \"treatment_regimen\", \"monotherapy_combination\", \"type_of_combination\", \"control_regimen\", \"type_of_control\", \"primary_endpoint\", \"secondary_endpoint\", \"follow_up_duration_for_primary_endpoint_s_in_months_overall\" FROM public.\"clinical_trials\" WHERE \"trial_phase\" = 'Phase 2' AND \"cancer_type\" = 'Pancreatic' AND \"class_of_ici\" = 'CTLA4' AND \"type_of_combination\" ILIKE '%combination%'",
  "answer": "Phase 2 CTLA-4 combination trials for Pancreatic cancer are available. Review the listed trials for specific regimens and control regimens.",
  "assumptions": "Assuming 'CTLA-4' is mapped to 'CTLA4' in the 'class_of_ici' column and that 'type_of_combination' indicates combination therapy."
}