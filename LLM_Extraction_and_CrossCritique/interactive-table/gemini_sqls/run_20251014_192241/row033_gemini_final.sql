SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "ici_class" = 'PD1' AND "primary_endpoint_is_multiple_or_composite" IS NOT NULL;