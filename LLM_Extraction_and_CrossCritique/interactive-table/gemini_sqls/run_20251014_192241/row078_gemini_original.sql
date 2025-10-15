SELECT "nct", "author", "year", "pubmed_id", "treatment_regimen", "combination_type", "ici_name"
FROM public."clinical_trials"
WHERE "trial_phase" = 'Phase 3'
  AND "cancer_type" = 'NSCLC'
  AND "ici_class" = 'PD-1'
  AND "therapy_modality" = 'Combination';