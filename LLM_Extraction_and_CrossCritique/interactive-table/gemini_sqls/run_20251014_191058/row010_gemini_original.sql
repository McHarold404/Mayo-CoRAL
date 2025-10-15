SELECT "nct", "author", "year", "pubmed_id", "other_biomarker_inclusion", "cancer_type"
FROM public."clinical_trials"
WHERE "cancer_type" = 'SCLC' AND "other_biomarker_inclusion" = 'Yes';