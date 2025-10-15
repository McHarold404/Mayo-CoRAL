SELECT "nct", "author", "year", "publication_type", "cancer_type", "follow_up_duration_overall_months", "follow_up_duration_rx_months", "follow_up_duration_control_months"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Esophageal/GEJ';