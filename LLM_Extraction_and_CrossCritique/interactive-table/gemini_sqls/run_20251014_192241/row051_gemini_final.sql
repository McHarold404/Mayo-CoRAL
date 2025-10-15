SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "ici_class", "pdl1_inclusion" 
FROM public."clinical_trials"
WHERE "cancer_type" = 'HNSCC' AND "ici_class" = 'PD-L1' AND "pdl1_inclusion" = 'Yes';