SELECT "nct", "author", "year", "pubmed_id", "total_sample_size" 
FROM public."clinical_trials"
WHERE "cancer_type" ILIKE '%Renal cell%' 
  AND "ici_name" = 'Pembrolizumab'
  AND "monotherapy_combination" = 'Combination therapy';