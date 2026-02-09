SELECT "nct", "author", "year", "publication_type", "lines_of_treatment", "therapy_modality", "cancer_type", "combination_type", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Melanoma' AND NULLIF(regexp_replace(("lines_of_treatment")::text, '[^0-9\.-]', '', 'g'), '')::numeric >= 2 AND "therapy_modality" = 'Combination';