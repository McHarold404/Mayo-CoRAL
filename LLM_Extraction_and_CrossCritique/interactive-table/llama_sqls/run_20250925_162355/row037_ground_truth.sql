SELECT "nct", "author", "year", "publication_type", "trial_phase", "ici_class", "therapy_modality", "cancer_type", "ici_name", "treatment_regimen"
FROM public."clinical_trials"
WHERE "ici_class" = 'PD-L1' AND "cancer_type" = 'Breast' AND "trial_phase" = 'Phase 2' AND "therapy_modality" = 'Monotherapy';