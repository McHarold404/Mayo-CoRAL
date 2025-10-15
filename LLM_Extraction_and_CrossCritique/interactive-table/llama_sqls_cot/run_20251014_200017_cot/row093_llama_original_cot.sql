SELECT "nct", "author", "year", "pubmed_id", "trial_name", "treatment_regimen", "trial_phase", "ici_name", "cancer_type"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Colorectal' AND "ici_name" IN ('Durvalumab', 'Tremelimumab') AND "trial_phase" = 'Phase 2';