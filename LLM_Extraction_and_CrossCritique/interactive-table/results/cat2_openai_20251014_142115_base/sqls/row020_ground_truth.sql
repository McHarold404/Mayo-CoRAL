SELECT "nct", "author", "year", "publication_type", "ici_name", "trial_phase", "cancer_type"
FROM public."clinical_trials"
WHERE "ici_name" = 'Pembrolizumab' AND "cancer_type" = 'Melanoma' AND "trial_phase" = 'Phase 2' AND "publication_type" = 'Original publication';