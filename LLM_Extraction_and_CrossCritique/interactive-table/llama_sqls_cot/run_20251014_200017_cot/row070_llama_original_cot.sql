SELECT "nct", "author", "year", "pubmed_id", "trial_name", "trial_phase", "ici_name", "cancer_type", "therapy_modality", "combination_type", "control_regimen", "primary_endpoint"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Esophageal/GEJ' AND "ici_name" = 'Pembrolizumab' AND "trial_phase" = 'Phase 3';