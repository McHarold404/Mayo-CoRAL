SELECT "nct", "author", "year", "pubmed_id", "total_sample_size", "combination_type"
FROM public."clinical_trials"
WHERE "ici_name" = 'Ipilimumab'
  AND "cancer_type" = 'Melanoma'
  AND "monotherapy_combination" = 'Combination therapy';