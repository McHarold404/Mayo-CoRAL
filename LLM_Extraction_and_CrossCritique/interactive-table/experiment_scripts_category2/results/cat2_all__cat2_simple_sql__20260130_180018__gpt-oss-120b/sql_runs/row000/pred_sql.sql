SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "cancer_type" ILIKE '%melanoma%'
  AND "type_of_combination" ILIKE '%vaccine%'
  AND ("class_of_ici" IS NOT NULL OR "name_of_ici" IS NOT NULL);