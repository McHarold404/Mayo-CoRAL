SELECT "nct", "author", "year", "pubmed_id" 
FROM public."clinical_trials"
WHERE "cancer_type" ILIKE '%Breast%'
  AND "treatment_regimen" ILIKE '%Chemotherapy%'
  AND "follow_up_duration_overall_months" > 21