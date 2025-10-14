SELECT "nct", "author", "year", "pubmed_id" 
FROM public."clinical_trials"
WHERE "cancer_type" ILIKE '%Colorectal%'
  AND "trial_phase" = 'Phase 3'
  AND "ici_class" IN ('PD-1', 'PD-L1', 'CTLA-4')
  AND "control_type" = 'Chemo';