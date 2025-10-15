SELECT "nct", "author", "year", "pubmed_id", "primary_endpoint", "combination_type", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Bladder/Urothelial' AND "combination_type" = 'ICI+Chemo';