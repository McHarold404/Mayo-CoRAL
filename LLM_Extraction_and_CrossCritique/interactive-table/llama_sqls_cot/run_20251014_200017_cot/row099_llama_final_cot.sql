SELECT "nct", "author", "year", "pubmed_id", "included_in_ma", "ici_class", "cancer_type", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "included_in_ma" = 'Yes' AND "cancer_type" = 'SCLC' AND "ici_class" IN ('PD-L1', 'CTLA-4');