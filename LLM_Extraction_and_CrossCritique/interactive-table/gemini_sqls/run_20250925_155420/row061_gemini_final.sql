SELECT "nct", "author", "year", "pubmed_id" 
FROM public."clinical_trials"
WHERE "cancer_type" ILIKE '%NSCLC%'
  AND "ici_name" ILIKE '%Nivolumab%'
  AND "ici_name" ILIKE '%Ipilimumab%'
  AND "follow_up_duration_overall_months" > 21;