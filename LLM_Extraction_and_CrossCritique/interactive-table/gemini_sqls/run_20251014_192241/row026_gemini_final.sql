SELECT "nct", "author", "year", "pubmed_id", "ici_class", "cancer_type", "pdl1_inclusion"
FROM public."clinical_trials"
WHERE "cancer_type" = 'RCC' AND "ici_class" = 'PD-L1' AND "pdl1_inclusion" IS NOT NULL;