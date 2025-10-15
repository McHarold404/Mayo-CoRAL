SELECT "nct", "author", "year", "publication_type", "cancer_type", "ici_class"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Gastric/GEJ' AND "ici_class" = 'PD-L1' AND "year" >= 2018;