SELECT "nct", "author", "year", "pubmed_id", "other_biomarker_inclusion"
FROM public."clinical_trials"
WHERE "cancer_type" = 'HCC' AND "other_biomarker_inclusion" = 'Yes' AND "pdl1_inclusion" = 'No';