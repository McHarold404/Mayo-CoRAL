SELECT "nct", "author", "year", "publication_type", "combination_type", "cancer_type", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Melanoma' AND "combination_type" = 'ICI+Vaccine';