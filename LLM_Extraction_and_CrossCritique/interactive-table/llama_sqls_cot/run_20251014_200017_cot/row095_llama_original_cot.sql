SELECT "nct", "author", "year", "publication_type", "ici_class", "cancer_type", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Mesothelioma' AND "ici_class" = 'PD1' AND "year" >= 2018;