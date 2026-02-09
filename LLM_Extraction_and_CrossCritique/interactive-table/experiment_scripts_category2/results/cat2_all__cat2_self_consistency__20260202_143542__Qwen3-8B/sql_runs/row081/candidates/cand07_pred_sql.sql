with median follow-up and show the months by arm.

The column "cancer_type" is likely to contain the specific type of cancer, so we should filter where "cancer_type" = 'Hodgkin Lymphoma'. However, it's possible that the data might have variations in spelling or formatting, so using ILIKE with %Hodgkin Lymphoma% could be more inclusive. But since the user specified exact match, we'll use equality.

Next, the user wants to show the months by arm. The columns that might be relevant here are "follow_up_duration_for_primary_endpoint_s_in_months_overall", "follow_up_duration_for_primary_endpoint_s_in_months_rx", and "follow_up_duration_for_primary_endpoint_s_in_months_control". These columns likely represent the follow-up duration for the primary endpoints in different arms (overall, treatment arm, and control arm, respectively).

The user mentioned "median follow-up", which might refer to the overall median follow-up duration. However, the exact interpretation of "median follow-up" from the data isn't clear. Since the columns provided are specific durations, we can assume that the user wants to display these durations for each arm.

Now, we need to construct the SQL query. We'll select the relevant columns, filter for Hodgkin Lymphoma, and include the necessary follow-up durations. The user also wants the "nct", "author", "year", and "pubmed_id" in the output unless the question explicitly asks for a count or summary statistic. Since the question asks to show the months by arm, we should include those follow-up columns.

The query should look something like this:

SELECT 
    "nct",
    "author",
    "year",
    "pubmed_id",
    "follow_up_duration_for_primary_endpoint_s_in_months_overall",
    "follow_up_duration_for_primary_endpoint_s_in_months_rx",
    "follow_up_duration_for_primary_endpoint_s_in_months_control"
FROM 
    public."clinical_trials"
WHERE 
    "cancer_type" = 'Hodgkin Lymphoma';