SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "treatment_regimen", "ici_name", "combination_type", "total_sample_size"
FROM public."clinical_trials"
WHERE "ici_name" = 'Pembrolizumab' AND "cancer_type" = 'RCC' AND "therapy_modality" = 'Combination';