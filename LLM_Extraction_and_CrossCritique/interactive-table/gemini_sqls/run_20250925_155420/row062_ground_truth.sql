SELECT "nct", "author", "year", "publication_type", "other_biomarker_inclusion", "cancer_type", "primary_endpoint"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Gastric/GEJ' AND "other_biomarker_inclusion" = 'Yes';