SELECT "nct", "author", "year", "publication_type", "trial_phase", "control_type", "cancer_type", "ici_name", "treatment_regimen"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Small Cell Lung' AND "trial_phase" = 'Phase 3' AND "control_type" = 'Chemo';