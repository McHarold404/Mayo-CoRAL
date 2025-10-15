SELECT "nct", "author", "year", "follow_up_duration_rx_months", "follow_up_duration_control_months", "cancer_type", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'RCC' AND "follow_up_duration_rx_months" IS NOT NULL AND "follow_up_duration_control_months" IS NOT NULL;