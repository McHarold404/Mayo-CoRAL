SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "ici_name", "ici_class", "pdl1_inclusion"
FROM public."clinical_trials"
WHERE "cancer_type" = 'NSCLC' AND "ici_class" = 'PD1' AND "pdl1_inclusion" = 'Yes';