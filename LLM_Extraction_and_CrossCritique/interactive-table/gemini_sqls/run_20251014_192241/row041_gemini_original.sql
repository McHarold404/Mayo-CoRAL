SELECT "nct", "author", "year", "cancer_type", "ici_class"
FROM public."clinical_trials"
WHERE "cancer_type" = 'NSCLC' AND "year" >= 2018 AND "ici_class" IN ('PD-L1', 'CTLA-4');