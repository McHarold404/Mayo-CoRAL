SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"follow_up_duration_for_primary_endpoint_s_in_months_overall\" AS overall, \"follow_up_duration_for_primary_endpoint_s_in_months_rx\" AS rx, \"follow_up_duration_for_primary_endpoint_s_in_months_control\" AS control FROM public.\"clinical_trials\" WHERE \"cancer_type\" ILIKE '%head%neck%'",
  "answer": "Retrieved Head and Neck trials with median follow-up durations by arm.",
  "assumptions": "Assumed that 'follow_up_duration_for_primary_endpoint_s_in_months_overall' represents median follow-up and that values are in months."
}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"follow_up_duration_for_primary_endpoint_s_in_months_overall\" AS overall_follow_up, \"follow_up_duration_for_primary_endpoint_s_in_months_rx\" AS rx_follow_up, \"follow_up_duration_for_primary_endpoint_s_in_months_control\" AS control_follow_up FROM public.\"clinical_trials\" WHERE \"cancer_type\" ILIKE '%head%neck%';