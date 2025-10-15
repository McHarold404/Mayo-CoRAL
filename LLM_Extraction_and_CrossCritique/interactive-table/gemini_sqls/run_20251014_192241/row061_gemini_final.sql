SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "cancer_type" = 'NSCLC' AND ("ici_name" = 'Nivolumab' OR "ici_name" = 'Ipilimumab') AND "follow_up_duration_overall_months" > 21;