SELECT "nct", "author", "year", "publication_type", "cancer_type", "therapy_modality", "trial_phase", "ici_name"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Breast' AND "clinical_setting_in_relation_to_surgery" = 'Neoadjuvant';