SELECT "nct", "author", "year", "pubmed_id", "treatment_regimen", "combination_type"
FROM public."clinical_trials"
WHERE "trial_phase" = 'Phase 2' AND "ici_class" = 'CTLA-4' AND "cancer_type" = 'NSCLC' AND "therapy_modality" = 'Combination';