SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "follow_up_duration_overall_months", "follow_up_duration_rx_months", "follow_up_duration_control_months"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Esophageal/GEJ' AND "follow_up_duration_overall_months" IS NOT NULL AND "follow_up_duration_rx_months" IS NOT NULL AND "follow_up_duration_control_months" IS NOT NULL;