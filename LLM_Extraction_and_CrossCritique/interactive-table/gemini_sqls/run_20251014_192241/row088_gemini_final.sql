SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Colorectal' AND NULLIF(regexp_replace(("lines_of_treatment")::text, '[^0-9\.-]', '', 'g'), '')::numeric >= 2 AND "therapy_modality" = 'Combination';