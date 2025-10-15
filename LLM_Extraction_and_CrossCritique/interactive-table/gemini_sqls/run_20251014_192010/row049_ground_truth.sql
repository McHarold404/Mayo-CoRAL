SELECT "nct", "author", "year", "publication_type", "ici_class", "cancer_type", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Head and Neck' AND "ici_class" = 'PD-L1, CTLA-4' AND NULLIF(regexp_replace(("year")::text, '[^0-9\.-]', '', 'g'), '')::numeric >= 2018;