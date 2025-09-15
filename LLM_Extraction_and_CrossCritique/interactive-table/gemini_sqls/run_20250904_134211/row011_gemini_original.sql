SELECT "nct", "author", "year", "cancer_type", "ici_class", "trial_phase", "total_sample_size"
FROM public."clinical_trials"
WHERE "ici_name" = 'Ipilimumab'
  AND "cancer_type" = 'Melanoma'
  AND "combination_type" IS NOT NULL
  AND "combination_type" <> 'NA';