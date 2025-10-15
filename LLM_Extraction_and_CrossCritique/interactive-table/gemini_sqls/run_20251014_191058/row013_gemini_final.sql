SELECT "nct", "author", "year", "pubmed_id", "other_biomarker_inclusion"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Prostate' AND "other_biomarker_inclusion" IS NOT NULL;