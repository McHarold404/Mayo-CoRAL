SELECT "nct", "author", "year", "publication_type", "ici_name", "trial_phase", "cancer_type"
FROM public."clinical_trials"
WHERE "ici_name" = 'Atezolizumab' AND "cancer_type" = 'Non-Small Cell Lung' AND "trial_phase" = 'Phase 2' AND "publication_type" = 'Original publication';