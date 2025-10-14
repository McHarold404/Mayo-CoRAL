SELECT "nct", "author", "year", "publication_type", "ici_name", "follow_up_duration_overall_months", "cancer_type", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Breast' AND "ici_name" = 'Chemotherapy' AND NULLIF(regexp_replace(("follow_up_duration_overall_months")::text, '[^0-9\.-]', '', 'g'), '')::numeric > 21;