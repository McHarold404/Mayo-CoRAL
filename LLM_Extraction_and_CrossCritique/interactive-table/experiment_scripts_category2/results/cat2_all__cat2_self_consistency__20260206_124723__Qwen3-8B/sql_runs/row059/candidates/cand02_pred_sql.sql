SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "trial_phase" = 'Phase 3'
  AND (
    ("name_of_ici" = 'Nivolumab' OR "name_of_ici_1" = 'Nivolumab')
    AND ("name_of_ici" = 'Ipilimumab' OR "name_of_ici_1" = 'Ipilimumab')
  )
  AND "cancer_type" = 'Non-Small Cell Lung'
  AND "originial_publication_or_follow_up" = 'original publication';