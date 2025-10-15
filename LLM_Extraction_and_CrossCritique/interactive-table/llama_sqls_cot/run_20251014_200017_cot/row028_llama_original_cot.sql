SELECT "nct", "author", "year", "follow_up_duration_rx_months", "follow_up_duration_control_months", "cancer_type", "trial_phase", "follow_up_type"
FROM public."clinical_trials"
WHERE "cancer_type" = 'HNSCC' AND "follow_up_duration_rx_months" IS NOT NULL AND "follow_up_duration_control_months" IS NOT NULL;