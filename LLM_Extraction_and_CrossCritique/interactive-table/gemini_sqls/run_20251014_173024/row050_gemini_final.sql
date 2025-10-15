SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "cancer_type" ILIKE '%HNSCC%'
  AND "lines_of_treatment" ILIKE '%2L+%' 
  AND "therapy_type" = 'Combination therapy';