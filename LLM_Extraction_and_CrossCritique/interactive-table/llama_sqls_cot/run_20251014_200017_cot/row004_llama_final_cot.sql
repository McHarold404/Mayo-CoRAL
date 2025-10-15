SELECT "nct", "author", "year", "pubmed_id", "trial_name", "treatment_regimen", "combination_type", "trial_phase", "ici_name", "ici_class"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Melanoma' AND "ici_class" = 'CTLA4' AND "trial_phase" = 'Phase 3' AND "therapy_modality" = 'Combination';