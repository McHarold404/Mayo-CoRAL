SELECT "nct", "author", "year", "pubmed_id", "treatment_regimen"
FROM public."clinical_trials"
WHERE "trial_phase" = 'Phase 2' AND "ici_class" = 'PD-L1' AND "therapy_modality" = 'Monotherapy' AND "cancer_type" = 'Breast (TNBC)';