with %Head and Neck% to cover variations. 

For the PD-L1 class, the user mentioned PD-L1, but the column is "class_of_ici". The requirement says if PD-1 is mentioned, map to "PD1". However, here it's PD-L1, so I should check if the column has 'PD-L1' or maybe 'PD1' for PD-L1. Wait, the note says PD-1 maps to PD1, but PD-L1 is different. Wait, the instruction says: "If PD-1 is mentioned, map to 'PD1' for 'class_of_ici' (no dash)." So PD-L1 is not mentioned here. Wait, the question is about PD-L1, so maybe the class_of_ici would be 'PD-L1' or perhaps 'PD1'? Wait, the note only mentions PD-1, not PD-L1. So maybe the class_of_ici could be 'PD-L1' or 'PD1'? Hmm, but the user is asking for PD-L1. So maybe the correct value is 'PD-L1'. But I need to check if the data has that. However, the user might have stored PD-L1 as is. So I should check for 'PD-L1' in class_of_ici. 

Wait, the user's question is about PD-L1, so the class_of_ici should be 'PD-L1' or maybe 'PD1' if they mapped it. But according to the note, only PD-1 is mapped to PD1. So PD-L1 remains as is. So I need to look for 'PD-L1' in class_of_ici. 

Also, the inclusion criteria: the column is "is_pd_l1_positivity_inclusion_criteria". The value here should be 't' or 'true' to indicate that PD-L1 positivity was an inclusion criterion. 

So putting it all together: select trials where cancer_type is 'Head and Neck' (using ILIKE for possible variations), class_of_ici is 'PD-L1', and is_pd_l1_positivity_inclusion_criteria is true. 

Also, the user wants the nct, author, year, pubmed_id. So the SELECT list includes those columns. 

Wait, the requirements say that unless