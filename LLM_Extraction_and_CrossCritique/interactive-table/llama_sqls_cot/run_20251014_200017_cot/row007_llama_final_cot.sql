SELECT "nct", "author", "year", "treatment_regimen", "combination_type", "trial_phase", "ici_class", "cancer_type"
FROM public."clinical_trials"
WHERE "trial_phase" = 'Phase 2' AND "ici_class" = 'CTLA4' AND "therapy_modality" = 'Combination' AND "cancer_type" = 'NSCLC';