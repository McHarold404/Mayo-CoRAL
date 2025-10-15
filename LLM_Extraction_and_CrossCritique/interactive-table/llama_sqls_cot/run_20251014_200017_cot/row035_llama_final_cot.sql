SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "control_type", "control_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Gastric/GEJ' AND "control_type" = 'Placebo';