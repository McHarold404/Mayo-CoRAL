SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "other_biomarker_inclusion", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Melanoma' AND "other_biomarker_inclusion" IS NOT NULL AND "other_biomarker_inclusion" != 'None' AND "other_biomarker_inclusion" != 'NA' AND "other_biomarker_inclusion" != 'Unknown';