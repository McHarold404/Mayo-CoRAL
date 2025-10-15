SELECT "nct", "author", "year", "pubmed_id", "trial_name", "treatment_regimen", "trial_phase", "cancer_type", "ici_name"
FROM public."clinical_trials"
WHERE "cancer_type" = 'NSCLC' AND "ici_name" = 'Atezolizumab' AND "trial_phase" = 'Phase 3';