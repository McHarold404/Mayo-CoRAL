SELECT "nct", "author", "year", "primary_endpoint", "combination_type", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'SCLC' AND "combination_type" = 'ICI+ICI+Chemo';