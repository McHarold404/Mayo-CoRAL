SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "ici_name", "ici_class", "included_in_ma"
FROM public."clinical_trials"
WHERE "cancer_type" = 'NSCLC' AND "included_in_ma" = 'Yes' AND ("ici_class" = 'PD-L1' OR "ici_class" = 'CTLA-4');