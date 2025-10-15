SELECT "nct", "author", "year", "pubmed_id", "ici_name", "cancer_type", "therapy_modality", "combination_type", "total_sample_size"
FROM public."clinical_trials"
WHERE "ici_name" = 'Ipilimumab' AND "cancer_type" = 'Melanoma' AND "therapy_modality" = 'Combination';