SELECT "nct", "author", "year", "pubmed_id", "trial_phase", "ici_name", "cancer_type", "publication_type"
FROM public."clinical_trials"
WHERE "trial_phase" = 'Phase 3' AND "ici_name" IN ('Durvalumab', 'Tremelimumab') AND "cancer_type" = 'SCLC' AND "publication_type" = 'Follow-up'