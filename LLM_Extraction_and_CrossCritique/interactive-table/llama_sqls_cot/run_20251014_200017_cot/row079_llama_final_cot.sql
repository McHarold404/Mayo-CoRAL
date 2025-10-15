SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "ici_class", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Gastric/GEJ' AND "ici_class" = 'PD-L1' AND "year" >= 2018;