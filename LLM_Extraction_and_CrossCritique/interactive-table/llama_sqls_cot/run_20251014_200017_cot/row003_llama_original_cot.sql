SELECT "nct", "author", "year", "total_sample_size", "treatment_regimen", "combination_type", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Melanoma' AND "ici_name" = 'Ipilimumab' AND "therapy_modality" = 'Combination';