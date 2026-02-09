SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"cancer_type\" = 'Breast' AND \"type_of_therapy\" = 'Chemotherapy' AND \"follow_up_duration_for_primary_endpoint_s_in_months_overall\" > 21",
  "answer": "Breast Chemotherapy trials with overall follow-up exceeding 21 months are listed.",
  "assumptions": ""
}
</think>

{
  "sql": "SELECT \"nct\", \"author\", \"year\", \"pubmed_id\" FROM public.\"clinical_trials\" WHERE \"cancer_type\" = 'Breast' AND \"type_of_therapy\" = 'Chemotherapy' AND \"follow_up_duration_for_primary_endpoint_s_in_months_overall\" > 21",
  "answer": "Breast Chemotherapy trials with overall follow-up exceeding 21 months are listed.",
  "assumptions": ""
}