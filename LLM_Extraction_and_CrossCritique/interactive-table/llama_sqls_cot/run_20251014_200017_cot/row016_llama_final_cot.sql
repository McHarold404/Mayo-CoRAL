SELECT "nct", "author", "year", "pubmed_id", "included_in_ma", "ici_class", "cancer_type", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Melanoma' AND "ici_class" = 'CTLA4' AND "included_in_ma" = 'Yes';