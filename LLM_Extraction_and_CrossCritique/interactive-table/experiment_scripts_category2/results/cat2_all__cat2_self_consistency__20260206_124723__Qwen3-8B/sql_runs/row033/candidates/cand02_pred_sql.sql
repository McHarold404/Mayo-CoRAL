with %...% for free text. So maybe the column contains text that includes 'composite' or 'co-primary', so we can check for that. However, the column's name is a bit unclear. Alternatively, maybe the primary_endpoint or secondary_endpoint columns have that info. Wait, the columns are:

- primary_endpoint
- priamry_multiple_composite_or_co_primary_endpoints
- secondary_endpoint

So the column "priamry_multiple_composite_or_co_primary_endpoints" seems to be specifically for whether the trial reported multiple endpoints, composite or co-primary. So perhaps if that column is not null, it indicates that there are such endpoints. But again, without knowing the exact data, I'll have to make an assumption here.

The user's question is to list PD1 trials that reported composite or co-primary endpoints. So the steps are:

1. Filter rows where "class_of_ici" is 'PD1' (