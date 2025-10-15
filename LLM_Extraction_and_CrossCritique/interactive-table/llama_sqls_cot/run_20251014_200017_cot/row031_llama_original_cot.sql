SELECT "nct", "author", "year", "pubmed_id", "ici_class", "cancer_type", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'RCC' AND "ici_class" IN ('PD1', 'CTLA-4') AND "year" >= 2018;