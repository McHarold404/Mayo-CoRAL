SELECT "nct", "author", "year", "pubmed_id", "trial_name", "trial_phase", "treatment_regimen", "ici_name", "cancer_type"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Melanoma' AND "trial_phase" = 'Phase 3' AND "treatment_regimen" ILIKE '%Pembrolizumab%';