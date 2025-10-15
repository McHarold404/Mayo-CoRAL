SELECT "nct", "author", "year", "publication_type", "lines_of_treatment", "therapy_modality", "cancer_type", "combination_type", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Melanoma' AND "lines_of_treatment" ILIKE '%2L%' AND "therapy_modality" = 'Combination';