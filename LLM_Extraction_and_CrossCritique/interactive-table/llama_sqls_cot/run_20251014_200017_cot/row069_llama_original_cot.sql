SELECT "nct", "author", "year", "pubmed_id", "trial_phase", "cancer_type", "treatment_regimen", "control_regimen", "combination_type", "control_type"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Colorectal' AND "trial_phase" = 'Phase 3' AND "control_type" = 'Chemo' AND "therapy_modality" = 'Combination' AND "combination_type" = 'ICI + Chemo';