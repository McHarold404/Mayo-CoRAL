SELECT "nct", "author", "year", "pubmed_id", "cancer_type", "ici_class", "therapy_modality", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Esophageal/GEJ' AND "ici_class" = 'PD1' AND "year" >= 2018;