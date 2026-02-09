SELECT statement should include those columns. 

Let me check the column names again. The columns are "cancer_type", "is_any_other_biomarker_used_for_inclusion", "is_pd_l1_positivity_inclusion_criteria". 

So the SQL query would be:

SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Bladder'
AND "is_any_other_biomarker_used_for_inclusion" = true
AND "is_pd_l1_positivity_inclusion_criteria" = false;