SELECT "nct", "author", "year", "pubmed_id", "clinical_setting_in_relation_to_surgery", "cancer_type", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" LIKE '%Breast%' AND "clinical_setting_in_relation_to_surgery" = 'Neoadjuvant';