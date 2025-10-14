SELECT "nct", "author", "year", "publication_type", "other_biomarker_inclusion", "cancer_type", "primary_endpoint"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Non-Small Cell Lung' AND "other_biomarker_inclusion" = 'Yes';