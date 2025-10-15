SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "ici_name", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Pancreatic' AND "ici_name" = 'Pembrolizumab' AND "trial_phase" = 'Phase 2';