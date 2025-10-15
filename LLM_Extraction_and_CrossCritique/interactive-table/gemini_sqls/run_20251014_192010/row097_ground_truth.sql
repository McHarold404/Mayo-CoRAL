SELECT "nct", "author", "year", "publication_type", "ici_name", "trial_phase", "cancer_type"
FROM public."clinical_trials"
WHERE "ici_name" = 'Durvalumab, Tremelimumab' AND "cancer_type" = 'Small Cell Lung' AND "trial_phase" = 'Phase 3' AND "publication_type" = 'Follow-up';