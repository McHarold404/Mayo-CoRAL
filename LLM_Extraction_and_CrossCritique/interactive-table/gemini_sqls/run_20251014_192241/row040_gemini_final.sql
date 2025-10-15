SELECT "nct", "author", "year", "pubmed_id", "trial_name", "cancer_type", "ici_name", "ici_class", "primary_endpoint", "primary_endpoint_is_multiple_or_composite"
FROM public."clinical_trials"
WHERE "ici_class" = 'CTLA-4' AND "primary_endpoint_is_multiple_or_composite" IS NOT NULL;