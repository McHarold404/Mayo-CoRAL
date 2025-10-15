SELECT "nct", "author", "year", "pubmed_id", "treatment_regimen", "combination_type", "ici_name", "ici_class"
FROM public."clinical_trials"
WHERE "trial_phase" = 'Phase 2'
  AND "cancer_type" = 'NSCLC'
  AND "ici_class" = 'CTLA-4'
  AND "therapy_modality" = 'Combination';