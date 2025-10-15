SELECT "nct", "author", "year", "pubmed_id", "trial_name", "treatment_regimen", "ici_name", "ici_class", "therapy_modality", "trial_phase", "cancer_type"
FROM public."clinical_trials"
WHERE "trial_phase" = 'Phase 2' AND "ici_class" = 'PD-L1' AND "therapy_modality" = 'Monotherapy' AND "cancer_type" = 'Breast (TNBC)';