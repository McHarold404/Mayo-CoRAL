SELECT "nct", "author", "year", "publication_type", "ici_class", "cancer_type", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'HNSCC' AND "ici_class" IN ('PD-L1', 'CTLA-4') AND "year" >= 2018;