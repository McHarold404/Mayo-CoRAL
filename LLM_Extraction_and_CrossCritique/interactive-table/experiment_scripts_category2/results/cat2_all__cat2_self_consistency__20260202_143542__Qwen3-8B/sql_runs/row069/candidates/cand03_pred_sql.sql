select trials where "cancer_type" is 'Colorectal', "trial_phase" is '3', and the treatment regimen includes an ICI and the control regimen is Chemo. But how to represent this in SQL?

I need to check if the treatment regimen includes ICI (like PD1 or PD-L1) and the control regimen is Chemo. Alternatively, the "class_of_ici" and "name_of_ici" might