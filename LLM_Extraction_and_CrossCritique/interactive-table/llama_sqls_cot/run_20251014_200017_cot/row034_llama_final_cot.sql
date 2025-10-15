SELECT "nct", "author", "year", "pubmed_id", "ici_name", "ici_class", "pdl1_inclusion", "cancer_type", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Bladder/Urothelial' AND "ici_class" = 'PD1' AND "pdl1_inclusion" = 'Yes';