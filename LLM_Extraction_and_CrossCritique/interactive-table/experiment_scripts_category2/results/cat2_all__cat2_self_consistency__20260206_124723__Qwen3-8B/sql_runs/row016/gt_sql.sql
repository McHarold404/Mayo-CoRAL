SELECT "nct", "author", "year", "publication_type", "included_in_ma", "ici_class", "cancer_type", "ici_name"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Melanoma' AND "ici_class" = 'CTLA-4' AND "included_in_ma" = 'No';