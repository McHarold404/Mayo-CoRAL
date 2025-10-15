SELECT "nct", "author", "year", "pubmed_id", "treatment_regimen", "ici_name", "ici_class", "trial_phase", "cancer_type", "therapy_type"
FROM public."clinical_trials"
WHERE "trial_phase" = 'Phase 3' AND "ici_class" = 'PD-L1' AND "therapy_type" = 'Monotherapy' AND "cancer_type" = 'Colorectal';