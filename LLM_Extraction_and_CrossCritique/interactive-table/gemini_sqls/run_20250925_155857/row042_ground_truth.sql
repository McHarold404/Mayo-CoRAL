SELECT "nct", "author", "year", "publication_type", "ici_class", "primary_endpoint_is_multiple_or_composite", "ici_name", "primary_endpoint"
FROM public."clinical_trials"
WHERE "ici_class" = 'PD-L1, CTLA-4' AND "primary_endpoint_is_multiple_or_composite" = 'Multiple';