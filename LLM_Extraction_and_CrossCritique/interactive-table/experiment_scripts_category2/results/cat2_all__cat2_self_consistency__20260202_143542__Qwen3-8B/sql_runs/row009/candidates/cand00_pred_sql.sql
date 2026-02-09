with minimum follow-up and show months by arm. 

First, I need to identify the relevant columns. The cancer_type should be 'Small Cell Lung'. The follow-up durations are in columns like follow_up_duration_for_primary_endpoint_s_in_months_overall, follow_up_duration_for_primary_endpoint_s_in_months_rx, and follow_up_duration_for_primary_endpoint_s_in_months_control. Since the question mentions "by arm," I should consider each arm's follow-up. But wait, the columns might already be structured per arm. Wait, the columns are follow_up_duration_for_primary_endpoint_s_in_months_overall, which might be the overall, and then follow_up_duration_for_primary_endpoint_s_in_months_rx and follow_up_duration_for_primary_endpoint_s_in_months_control. But I need to check if those are per arm or not. 

The user wants the minimum follow-up. So I need to find the minimum value across those columns. However, the exact columns might be named differently. Let me check the columns again. The columns are follow_up_duration_for_primary_endpoint_s_in_months_overall, follow_up_duration_for_primary_endpoint_s_in_months_rx, and follow_up_duration_for_primary_endpoint_s_in_months_control. Wait, maybe the overall is the total, and rx and control are the arms. So to get the minimum follow-up per trial, I need to consider all three. But the user might want the minimum of each trial's follow-up across arms. 

So I should select the trial details, and for each trial, compute the minimum of those three columns. But the columns are numeric, so using MIN() on them. However, the user wants to show the months by arm. Maybe they want to see each arm's follow-up duration. But the question says "minimum follow-up" so perhaps the minimum of all arms for each trial. 

Wait, the user says "show months by arm." So perhaps they want to display the follow-up duration for each arm. But the columns are named with rx and control, so maybe those are the arms. So the query should include those columns. 

But the user wants trials with minimum follow-up. So perhaps they want trials where the follow-up duration is the minimum. But that's ambiguous. Alternatively, they might want to find trials that have a minimum follow-up duration (like the shortest duration) and show the months per arm. 

Alternatively, maybe the user wants to find trials where the follow-up is at least a certain minimum, but the question says "minimum follow-up" which is a bit unclear. But the exact question is "Find Small Cell Lung trials with minimum follow‑up and show months by arm." So perhaps they want trials that have the minimum follow-up duration, and show the months per arm. 

But how to determine the minimum? Maybe the user wants to find the trials