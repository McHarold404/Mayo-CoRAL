SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "treatment_regimen", "follow_up_duration_overall_months"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Breast' AND "treatment_regimen" ILIKE '%Chemo%' AND "follow_up_duration_overall_months" > 21;