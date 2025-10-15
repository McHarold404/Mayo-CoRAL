SELECT "nct", "author", "year", "pubmed_id", "trial_name", "treatment_regimen", "combination_type", "trial_phase", "ici_name", "ici_class"
FROM public."clinical_trials"
WHERE "trial_phase" = 'Phase 3' AND "cancer_type" = 'NSCLC' AND "ici_class" = 'PD1' AND "therapy_modality" = 'Combination';