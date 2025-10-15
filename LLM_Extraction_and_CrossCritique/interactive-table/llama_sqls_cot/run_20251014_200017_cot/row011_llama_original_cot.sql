SELECT "nct", "author", "year", "ici_class", "cancer_type", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Prostate' AND "ici_class" = 'CTLA4' AND "year" >= 2018;