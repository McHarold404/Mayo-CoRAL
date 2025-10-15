SELECT "nct", "author", "year", "publication_type", "control_type", "cancer_type", "control_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Small Cell Lung' AND "control_type" = 'Chemo';