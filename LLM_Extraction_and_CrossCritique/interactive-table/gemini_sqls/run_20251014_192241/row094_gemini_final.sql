SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Mesothelioma' AND "ici_name" IN ('Nivolumab', 'Ipilimumab') AND "follow_up_duration_overall_months" > 21;