SELECT "nct", "author", "year", "pubmed_id", "other_biomarker_inclusion", "cancer_type"
FROM public."clinical_trials"
WHERE "cancer_type" = 'RCC' AND "other_biomarker_inclusion" ILIKE '%Yes%';