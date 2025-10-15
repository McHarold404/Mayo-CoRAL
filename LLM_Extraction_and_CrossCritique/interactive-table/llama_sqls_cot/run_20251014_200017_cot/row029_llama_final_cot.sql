SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "other_biomarker_inclusion", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'HNSCC' AND "other_biomarker_inclusion" IS NOT NULL AND "pdl1_inclusion" IS NULL;