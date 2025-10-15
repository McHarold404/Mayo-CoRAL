SELECT "nct", "author", "year", "pubmed_id", "trial_name", "trial_phase", "cancer_type", "treatment_regimen", "control_regimen", "control_type"
FROM public."clinical_trials"
WHERE "cancer_type" = 'SCLC' AND "trial_phase" = 'Phase 3' AND "therapy_type" = 'Combination' AND "combination_type" = 'ICI + Chemo' AND "control_type" = 'Chemo';