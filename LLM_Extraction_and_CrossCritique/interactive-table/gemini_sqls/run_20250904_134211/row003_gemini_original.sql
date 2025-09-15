SELECT "nct", "author", "year", "cancer_type", "ici_class", "trial_phase", "primary_endpoint" 
FROM public."clinical_trials"
WHERE "cancer_type" ILIKE '%SCLC%' 
  AND "combination_type" = 'ICI + ICI + Chemo';