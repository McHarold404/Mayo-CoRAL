SELECT "nct", "author", "year", "follow_up_duration_rx_months", "follow_up_duration_control_months", "cancer_type", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Melanoma' AND "follow_up_duration_rx_months" IS NOT NULL AND "follow_up_duration_control_months" IS NOT NULL
ORDER BY "follow_up_duration_rx_months" ASC, "follow_up_duration_control_months" ASC
LIMIT 1;