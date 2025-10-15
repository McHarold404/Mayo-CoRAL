SELECT "nct", "author", "year", "pubmed_id", "ici_class", "cancer_type", "included_in_ma"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Melanoma' AND "ici_class" = 'CTLA-4' AND "included_in_ma" = 'Yes';