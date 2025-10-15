SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "ici_class"
FROM public."clinical_trials"
WHERE "cancer_type" = 'HNSCC' AND "ici_class" IN ('PD-L1', 'CTLA-4') AND "year" >= 2018;