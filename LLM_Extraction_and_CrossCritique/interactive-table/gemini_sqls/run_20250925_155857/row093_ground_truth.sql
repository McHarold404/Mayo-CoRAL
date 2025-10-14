SELECT "nct", "author", "year", "publication_type", "ici_name", "trial_phase", "cancer_type", "trial_name", "treatment_regimen"
FROM public."clinical_trials"
WHERE "ici_name" = 'Durvalumab, Tremelimumab' AND "cancer_type" = 'Colorectal' AND "trial_phase" = 'Phase 2';