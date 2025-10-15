SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "ici_name", "follow_up_duration_overall_months"
FROM public."clinical_trials"
WHERE "cancer_type" = 'HNSCC' AND "ici_name" = 'Nivolumab' AND "follow_up_duration_overall_months" > 21;