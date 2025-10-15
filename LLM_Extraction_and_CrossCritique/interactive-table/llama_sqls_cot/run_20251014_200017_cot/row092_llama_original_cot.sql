SELECT "nct", "author", "year", "pubmed_id", "treatment_regimen", "combination_type", "cancer_type", "total_sample_size"
FROM public."clinical_trials"
WHERE "ici_name" = 'Pembrolizumab' AND "therapy_modality" = 'Combination' AND "cancer_type" = 'RCC';