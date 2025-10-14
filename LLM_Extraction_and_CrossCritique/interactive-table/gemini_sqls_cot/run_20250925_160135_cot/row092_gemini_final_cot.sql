SELECT "nct", "author", "year", "pubmed_id", "total_sample_size", "combination_type"
FROM public."clinical_trials"
WHERE "ici_name" = 'Pembrolizumab'
AND "cancer_type" ILIKE '%Renal cell%' 
AND "monotherapy" = 'Combination therapy';