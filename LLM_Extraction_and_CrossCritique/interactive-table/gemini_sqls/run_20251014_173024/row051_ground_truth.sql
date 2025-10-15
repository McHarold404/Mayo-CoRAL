SELECT "nct", "author", "year", "publication_type", "pdl1_inclusion", "ici_class", "cancer_type", "ici_name", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Head and Neck' AND "ici_class" = 'PD-L1' AND "pdl1_inclusion" = 'Yes';