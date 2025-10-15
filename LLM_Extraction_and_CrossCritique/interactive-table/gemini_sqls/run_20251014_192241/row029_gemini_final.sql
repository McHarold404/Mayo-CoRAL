SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "other_biomarker_inclusion"
FROM public."clinical_trials"
WHERE "cancer_type" = 'HNSCC' AND "other_biomarker_inclusion" != '';