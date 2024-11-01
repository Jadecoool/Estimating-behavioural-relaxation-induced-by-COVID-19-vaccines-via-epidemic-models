# Estimating-behavioural-relaxation-induced-by-COVID-19-vaccines-via-epidemic-models
Data and code for the paper Estimating behavioural relaxation induced by COVID-19 vaccines via epidemic models
# Abstract
The rollout of COVID-19 vaccines has been challenged by logistical issues, limited availability of doses, scarce healthcare capacity, spotty acceptance, and variants of concern. Non-pharmaceutical interventions (NPIs) have been critical to support these phases. At the same time, the arrival of vaccines might have changed the risk assessment of some leading to a behavioural relaxation of NPIs. Several epidemic models have investigated the potential effects of this phenomenon on the Pandemic, but they have not been validated against data. Recent empirical evidence, obtained via surveys, provides conflicting results on the matter. Hence, the extent behavioural relaxation induced by COVID-19 vaccines is still far from clear. Here, we aim to study this phenomenon in four regions. To this end, we implement five realistic epidemic models which include age structure, multiple strains, NPIs, and vaccinations. One of the models acts as a baseline, while the other four extend it and, building on the literature, include different behavioural relaxation mechanisms. First, we set the stage by calibrating the baseline model and running counterfactual scenarios to quantify the impact of vaccination and NPIs. Our results confirm the critical role of both in reducing infection and mortality rates. Second, we calibrate the four behavioural models and compare them to each other and to the baseline. While behavioural models offer a better fit of weekly deaths in all regions, this improvement is offset by their increased complexity in three locations. In the region where a behavioural model emerges as the most likely, our findings suggest that relaxation of NPIs led to a relative increase of deaths of more than $8\%$, highlighting the potential negative effect of this phenomenon. Overall, our work contributes to the retrospective validation of epidemic models developed amid the COVID-19 Pandemic.
## Data
The data folder contains raw data (in the sub-folder demographic raw, epidemic raw, mobility raw) and processed data (in the sub-folder regions) that are used for running calibration and simulation for the four regions.
## Calibration
The calibration folder contains the codes for model calibration. We have 6 scripts for different models (the name starting with baseline, behaviour(model 1 and 2), variation(model 3 and 4)) and the other scripts are for running calibration for different regions and models.
## Simulation
The simulation folder contains the codes for running counterfactual scenarios and other simulations.
## Posteriors
The posteriors folder contains the posteriors of the four regions. CSV files are the sampled parameters and NPZ files are the sampled trajectories.
## Model_output
The model_output folder contains the results(trajectories) of counterfactual scenarios(labelled with 'no') and the original model(labelled with 'yes').
## Script_for_plots
The script_for_plots contains the scripts for generating plots in the paper.
