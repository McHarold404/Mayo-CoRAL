SELECT "nct","author","year","pubmed_id","treatment_regimen"
FROM public."clinical_trials"
WHERE "trial_phase" = 'Phase 3'
  AND "class_of_ici" = 'CTLA-4'
  AND "cancer_type" ILIKE '%Melanoma%'
  AND ("type_of_combination" IS NOT NULL AND "type_of_combination" <> '');