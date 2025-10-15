SELECT "nct", "author", "year", "pubmed_id", "primary_endpoint"
FROM public."clinical_trials"
WHERE "cancer_type" = 'NSCLC' AND "combination_type" = 'ICI+Chemo';