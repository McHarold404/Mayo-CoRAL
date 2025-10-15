SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "other_biomarker_inclusion", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Esophageal/GEJ' AND "other_biomarker_inclusion" IS NOT NULL AND "other_biomarker_inclusion" != 'PD-L1';