with %PD-L1% and %CTLA-4% in the "class_of_ici" and "name_of_ici" columns.

Additionally, the user is asking for trials conducted in 2018 or later, so the "year" should be >= 2018.

The "cancer_type" should be "Urothelial" as per the user's request.

I should construct the query to select the required columns and apply the filters.

I need to make sure that the query uses the correct column names with double quotes and qualifies the table as public."clinical_trials".

I should also use COUNT(DISTINCT "nct") if the user is asking for a count, but since the user is asking to "show" the trials, I should return the rows.

I need to include the "nct", "author", "year", and "pubmed_id" in the SELECT clause as per the requirements.

I should also check if the "class_of_ici" has "PD1" instead of "PD-L1" and map it accordingly, but since the user is asking for PD-L1, I should look for "PD-L1" in the class_of_ici column.

I should also