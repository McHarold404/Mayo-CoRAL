SELECT "nct", "author", "year", "publication_type", "ici_name", "trial_phase", "cancer_type"
FROM public."clinical_trials"
WHERE "ici_name" = 'Nivolumab, Ipilimumab' AND "cancer_type" = 'Non-Small Cell Lung' AND "trial_phase" = 'Phase 3' AND "publication_type" = 'Original publication';