SELECT "nct", "author", "year", "pubmed_id", "trial_phase", "control_type"
FROM public."clinical_trials"
WHERE "cancer_type" = 'NSCLC' AND "trial_phase" = 'Phase 2' AND "control_type" = 'Chemo' AND "therapy_modality" = 'Monotherapy';