SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "cancer_type" = 'NSCLC' AND "control_regimen" = 'Chemo/Anti-VEGF';