SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "cancer_type" = 'RCC' AND "ici_class" = 'PD1' AND "year" >= 2018;