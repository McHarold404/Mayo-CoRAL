SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Prostate' AND "ici_class" = 'CTLA-4' AND "year" >= 2018;