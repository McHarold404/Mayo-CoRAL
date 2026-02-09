with those fields.

So the SQL would select those columns from the table where cancer_type is 'Hepatocellular', name_of_ici is 'Pembrolizumab', and trial_phase is '3'. 

Wait, but what if the trial_phase is stored as 'Phase 3' or 'III'? The user's instruction says to use exact equality. So if the data has '3' as the value, then it's correct. But if it's stored as 'III', then the query would miss it. But since the user specified phase 3, maybe the data uses '3' as the value. 

Also, need to check if there are any other conditions. For example, maybe the trial_phase is part of a larger string, but the column is supposed to be an enumerated value. So using exact match is better.

So the query would be:

SELECT "nct", "author", "year", "pubmed_id"
FROM public."clinical_trials"
WHERE "cancer_type" = 'Hepatocellular'
AND "name_of_ici" = 'Pembrolizumab'
AND "trial_phase" = '3';