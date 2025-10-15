SELECT "nct", "author", "year", "pubmed_id", "trial_name", "treatment_regimen", "trial_phase", "cancer_type", "ici_name", "ici_class", "therapy_modality"
FROM public."clinical_trials"
WHERE "cancer_type" = 'HCC' AND "ici_name" = 'Pembrolizumab' AND "trial_phase" = 'Phase 3';