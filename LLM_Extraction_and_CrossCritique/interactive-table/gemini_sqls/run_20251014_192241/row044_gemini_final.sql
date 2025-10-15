SELECT "nct", "author", "year", "pubmed_id", "trial_phase", "ici_class", "combination_type", "cancer_type", "treatment_regimen", "control_regimen"
FROM public."clinical_trials"
WHERE "trial_phase" = 'Phase 3'
  AND "cancer_type" = 'NSCLC'
  AND "ici_class" IN ('PD-L1', 'CTLA-4')
  AND "therapy_modality" = 'Combination';