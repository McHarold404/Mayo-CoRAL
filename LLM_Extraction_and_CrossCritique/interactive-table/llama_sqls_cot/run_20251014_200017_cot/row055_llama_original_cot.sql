SELECT "nct", "author", "year", "pubmed_id", "primary_endpoint", "primary_endpoint_is_multiple_or_composite", "ici_name", "ici_class", "cancer_type"
FROM public."clinical_trials"
WHERE "ici_class" = 'PD-L1' AND "primary_endpoint_is_multiple_or_composite" = TRUE;