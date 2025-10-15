SELECT "nct", "author", "year", "pubmed_id", "trial_name", "ici_name", "cancer_type", "trial_phase", "publication_type"
FROM public."clinical_trials"
WHERE "ici_name" = 'Pembrolizumab' AND "cancer_type" = 'Melanoma' AND "trial_phase" = 'Phase 2' AND "publication_type" = 'Original publication';