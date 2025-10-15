SELECT "nct", "author", "year", "pubmed_id", "clinical_setting", "therapy_type", "treatment_regimen", "ici_name", "ici_class", "combination_type", "cancer_type"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Breast (TNBC)' AND "clinical_setting" = 'Neoadjuvant';