SELECT "nct", "author", "year", "pubmed_id", "ici_name", "ici_class", "cancer_type", "included_in_ma"
FROM public."clinical_trials"
WHERE "cancer_type" = 'SCLC' AND "included_in_ma" = 'Yes' AND ("ici_class" = 'PD-L1' OR "ici_class" = 'CTLA-4');