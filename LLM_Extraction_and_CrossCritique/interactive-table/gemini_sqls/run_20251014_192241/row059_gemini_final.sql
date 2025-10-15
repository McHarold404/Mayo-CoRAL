SELECT "nct", "author", "year", "pubmed_id", "ici_name", "ici_class", "cancer_type", "trial_phase", "publication_type"
FROM public."clinical_trials"
WHERE "trial_phase" = 'Phase 3' AND "ici_name" IN ('Nivolumab', 'Ipilimumab') AND "cancer_type" = 'NSCLC' AND "publication_type" = 'Original publication'