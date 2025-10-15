SELECT "nct", "author", "year", "treatment_regimen", "ici_name", "ici_class", "combination_type", "control_regimen", "trial_phase", "cancer_type"
FROM public."clinical_trials"
WHERE "trial_phase" = 'Phase 3' AND "ici_class" IN ('PD-L1', 'CTLA-4') AND "combination_type" = 'ICI + ICI' AND "cancer_type" = 'NSCLC';