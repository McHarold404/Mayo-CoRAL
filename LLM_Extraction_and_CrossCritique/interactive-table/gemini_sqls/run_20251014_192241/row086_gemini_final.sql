SELECT "nct", "author", "year", "pubmed_id", "treatment_regimen", "control_regimen"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Colorectal' AND "trial_phase" = 'Phase 3' AND "ici_class" = 'PD-L1' AND "therapy_modality" = 'Monotherapy';