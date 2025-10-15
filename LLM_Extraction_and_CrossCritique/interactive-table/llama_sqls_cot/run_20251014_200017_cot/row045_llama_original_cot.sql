SELECT "nct", "author", "year", "pubmed_id", "trial_name", "treatment_regimen", "trial_phase", "ici_name"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Pancreatic' AND "ici_name" = 'Pembrolizumab' AND "trial_phase" = 'Phase 2';