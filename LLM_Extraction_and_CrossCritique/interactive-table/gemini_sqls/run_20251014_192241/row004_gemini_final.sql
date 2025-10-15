SELECT "nct", "author", "year", "pubmed_id", "treatment_regimen", "control_regimen", "ici_name", "combination_type"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Melanoma' AND "trial_phase" = 'Phase 3' AND "ici_class" = 'CTLA-4' AND "therapy_modality" = 'Combination';