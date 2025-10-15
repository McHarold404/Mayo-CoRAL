SELECT "nct", "author", "year", "pubmed_id", "trial_name", "treatment_regimen", "trial_phase", "cancer_type", "ici_name", "publication_type"
FROM public."clinical_trials"
WHERE "ici_name" = 'Atezolizumab' AND "cancer_type" = 'NSCLC' AND "trial_phase" = 'Phase 2' AND "publication_type" = 'Original publication';