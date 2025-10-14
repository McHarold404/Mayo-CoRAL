SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "cancer_type" ILIKE '%Head and Neck%'
  AND "lines_of_treatment" LIKE '%2L%'  
  AND "monotherapy_combination" = 'Combination therapy';