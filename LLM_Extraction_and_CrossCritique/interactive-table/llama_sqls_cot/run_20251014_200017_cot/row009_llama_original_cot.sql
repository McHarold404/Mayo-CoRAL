SELECT "nct", "author", "year", "cancer_type", "follow_up_duration_rx_months", "follow_up_duration_control_months", "follow_up_duration_overall_months"
FROM public."clinical_trials"
WHERE "cancer_type" = 'SCLC' AND "follow_up_duration_overall_months" IS NOT NULL
ORDER BY "follow_up_duration_overall_months" ASC
LIMIT 1;