SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "treatment_regimen", "ici_name", "follow_up_duration_overall_months"
FROM public."clinical_trials"
WHERE "cancer_type" = 'NSCLC' AND "ici_name" IN ('Nivolumab', 'Ipilimumab') AND "follow_up_duration_overall_months" > 21;