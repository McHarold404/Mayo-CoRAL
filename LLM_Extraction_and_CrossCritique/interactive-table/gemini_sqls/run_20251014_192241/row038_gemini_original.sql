SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Bladder/Urothelial' AND "ici_class" = 'PD-L1' AND "year" >= 2018;