SELECT "nct", "author", "year", "publication_type", "trial_phase", "ici_class", "therapy_modality", "cancer_type", "ici_name", "treatment_regimen"
FROM public."clinical_trials"
WHERE "ici_class" = 'CTLA-4' AND "cancer_type" = 'Non-Small Cell Lung' AND "trial_phase" = 'Phase 2' AND "therapy_modality" = 'Combination';