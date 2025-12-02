SELECT "nct", "author", "year", "publication_type", "combination_type", "cancer_type", "treatment_regimen", "primary_endpoint"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Urothelial' AND "combination_type" = 'ICI+Chemo';