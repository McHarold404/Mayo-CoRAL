SELECT "nct", "author", "year", "pubmed_id", "trial_name", "ici_name", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Melanoma' AND "ici_name" = 'Pembrolizumab' AND "trial_phase" = 'Phase 3';