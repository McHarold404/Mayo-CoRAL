SELECT "nct", "author", "year", "pubmed_id", "treatment_regimen", "combination_type", "control_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Multiple Myeloma' AND "trial_phase" = 'Phase 3' AND "ici_class" = 'PD1' AND "therapy_modality" = 'Combination';