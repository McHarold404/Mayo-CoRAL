SELECT "nct", "author", "year", "publication_type", "ici_class", "cancer_type", "trial_phase"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Renal cell' AND "ici_class" = 'PD1, CTLA-4' AND NULLIF(regexp_replace(("year")::text, '[^0-9\.-]', '', 'g'), '')::numeric >= 2018;