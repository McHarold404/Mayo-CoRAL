SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "cancer_type" ILIKE '%Head and Neck%'
  AND "other_biomarker_inclusion" = 'Yes'
  AND "pdl1_inclusion" = 'No';