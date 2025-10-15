SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "ici_name", "ici_class", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'RCC' AND "ici_class" = 'PD1' AND "year" >= 2018;