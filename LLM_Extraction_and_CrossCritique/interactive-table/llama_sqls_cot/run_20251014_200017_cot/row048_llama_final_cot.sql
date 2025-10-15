SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "control_regimen", "control_type", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'NSCLC' AND "control_type" = 'Chemo/Anti-VEGF';