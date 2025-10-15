SELECT "nct", "author", "year", "trial_name", "treatment_regimen", "ici_name", "combination_type", "control_regimen", "primary_endpoint", "trial_phase", "cancer_type"
FROM public."clinical_trials"
WHERE "trial_phase" = 'Phase 3' AND "ici_class" = 'PD1' AND "therapy_modality" = 'Combination' AND "cancer_type" = 'Multiple Myeloma';