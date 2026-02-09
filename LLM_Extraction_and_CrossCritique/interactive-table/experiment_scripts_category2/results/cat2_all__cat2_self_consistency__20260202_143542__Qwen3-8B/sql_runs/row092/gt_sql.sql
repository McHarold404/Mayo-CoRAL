SELECT "nct", "author", "year", "publication_type", "ici_name", "therapy_modality", "cancer_type", "total_sample_size", "trial_phase"
FROM public."clinical_trials"
WHERE "ici_name" = 'Pembrolizumab' AND "cancer_type" = 'Renal cell' AND "therapy_modality" = 'Combination';