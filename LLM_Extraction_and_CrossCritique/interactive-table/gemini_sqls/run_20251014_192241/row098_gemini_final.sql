SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "combination_type", "primary_endpoint"
FROM public."clinical_trials"
WHERE "cancer_type" = 'SCLC' AND "combination_type" = 'ICI+ICI+Chemo';