SELECT "nct", "author", "year", "pubmed_id", "trial_name", "publication_type", "ici_name", "ici_class", "therapy_modality", "combination_type", "cancer_type", "trial_phase", "treatment_regimen"
FROM public."clinical_trials"
WHERE "publication_type" = 'Follow-up' AND "trial_phase" = 'Phase 3' AND "cancer_type" = 'SCLC' AND ("ici_name" = 'Durvalumab' OR "ici_name" = 'Tremelimumab');