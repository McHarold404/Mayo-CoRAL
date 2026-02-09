SELECT COUNT(DISTINCT "nct"), "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "trial_phase" = 'Phase 3'
  AND "class_of_ici" = 'PD1'
  AND "type_of_combination" = 'Combination'
  AND "cancer_type" = 'Non-Small Cell Lung Cancer';