SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "cancer_type" ILIKE '%Hepatocellular%'
  AND "is_any_other_biomarker_used_for_inclusion" = true;