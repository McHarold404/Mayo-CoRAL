SELECT "nct", "author", "year", "publication_type", "control_type", "cancer_type", "control_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Gastric/GEJ' AND "control_type" = 'Placebo';