SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "cancer_type" = 'NSCLC' AND "ici_class" = 'PD1' AND "pdl1_inclusion" IS NOT NULL;