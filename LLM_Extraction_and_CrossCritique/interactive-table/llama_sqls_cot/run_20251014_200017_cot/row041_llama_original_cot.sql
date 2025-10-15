SELECT "nct", "author", "year", "pubmed_id", "ici_class", "cancer_type", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "year" >= 2018 AND "cancer_type" = 'NSCLC' AND "ici_class" IN ('PD-L1', 'CTLA-4');