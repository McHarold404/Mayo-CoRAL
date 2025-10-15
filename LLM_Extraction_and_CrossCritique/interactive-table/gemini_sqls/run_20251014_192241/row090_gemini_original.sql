SELECT "nct", "author", "year", "pubmed_id", "ici_class", "cancer_type", "pdl1_inclusion"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Breast (TNBC)' AND "ici_class" = 'PD1' AND "pdl1_inclusion" = 'Yes'