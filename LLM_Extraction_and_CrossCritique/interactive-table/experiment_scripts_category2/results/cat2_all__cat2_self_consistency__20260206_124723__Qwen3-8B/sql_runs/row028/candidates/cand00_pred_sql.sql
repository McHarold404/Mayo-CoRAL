with any assumptions made (empty if none).
- "sql" is a valid PostgreSQL SELECT statement that can be run directly.
- Do not include any other text.

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"follow_up_duration_for_primary_endpoint_s_in_months_overall\" AS overall_follow_up, \"follow_up_duration_for_primary_endpoint_s_in_months_rx\" AS rx_follow_up, \"follow_up_duration_for_primary_endpoint_s_in_months_control\" AS control_follow_up FROM public.\"clinical_trials\" WHERE \"cancer_type\" ILIKE '%head and neck%'",
  "answer": "Retrieved Head and Neck trials with median follow-up duration by arm.",
  "assumptions": "Assumed that 'follow_up_duration_for_primary_endpoint_s_in_months_overall' represents median follow-up and that 'rx_follow_up' and 'control_follow_up' correspond to treatment and control arms respectively."
}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\", \"follow_up_duration_for_primary_endpoint_s_in_months_overall\" AS overall_follow_up, \"follow_up_duration_for_primary_endpoint_s_in_months_rx\" AS rx_follow_up, \"follow_up_duration_for_primary_endpoint_s_in_months_control\" AS control_follow_up FROM public.\"clinical_trials\" WHERE \"cancer_type\" ILIKE '%head and neck%'",
  "answer": "Retrieved Head and Neck trials with median follow-up duration by arm.",
  "assumptions": "Assumed that 'follow_up_duration_for_primary_endpoint_s_in_months_overall' represents median follow-up and that 'rx_follow_up' and 'control_follow_up' correspond to treatment and control arms respectively."
}