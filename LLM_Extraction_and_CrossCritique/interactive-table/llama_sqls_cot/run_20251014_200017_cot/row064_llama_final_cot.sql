SELECT "nct", "author", "year", "pubmed_id", "ici_class", "cancer_type", "treatment_regimen", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Bladder/Urothelial' AND ("ici_class" = 'PD-L1' OR "ici_class" = 'CTLA-4') AND "year" >= 2018;