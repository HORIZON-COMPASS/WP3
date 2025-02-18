# Exposure and vulnerability modelling
This work is part of work package 3 of the COMPASS project, whose overarching objective is to characterise compound extremes in current and future climates. COMPASS (COMPound extremes Attribution of climate change: towardS an operational Service) aims to develop a harmonized, yet flexible, methodological framework for **climate and impact attribution** of various complex **extremes** that include compound, sequential and cascading hazard events. For more information and useful links about the project, have a look at the introduction on the [COMPASS Github repository](https://github.com/HORIZON-COMPASS).

<img src="https://naturalhazards.eu/compass.png" alt="logoCOMPASS" style="max-width: 50%;">

## Description

This code currently includes:
- preliminary version of global exposure model, 1850-2100
- windstorm damage and climate counterfactual calculation for Xynthia case study (UC1)

The code is under development and this file will be updated to reflect the current updates on the project.

### Global exposure model

The global exposure model forms Deliverable 3.1. The code enables generating a gridded dataset of global exposure (population, gross domestic product and net fixed asset value) in resolution of 30 arc seconds (1.85 km at the equator) and lower, spanning years 1850 to 2100 at annual resolution, including five future trajectories consistent with the Shared Socio-economic Pathways (SSPs). 

### UC1 France - 2010 Xynthia flood and windstorm

The goal of this case study, forming part of D4.1, is creating an attribution modelling chain considering the compound (spatially co-occurring due to a common meteorological cause) coastal flood and windstorm impacts. The full code is still in development until August 2025.

## Installation instructions

The code can be used by cloning the git repository and creating a conda virtual environment using `requirements.txt`. This code was created and tested with Python 3.11.

## How to run

### Global exposure model

To run the code, input data from the Zenodo repository is needed [link to be added]. Further steps are as follows:

1. The folder with data needs to be specified in `exposure_functions.py` under MAIN_PATH variable.
2. External public datasets, which we too large to include in the repository. In the folders GHSL/, HYDE/zip/ and Wang_SSP/, `download_data.txt` specifies where data can be found and provides a list of necessary files. GHSL data are needed in any case, while other data are only needed if the user wants to include pre-1975 or post-2020 timesteps. 
3. Once input data are in place, `disaggregation_exposure.py` can be run to generate the exposure dataset. The user can specify the following parameters:
- **Harmonize**: apply the harmonization procedure of historical and projected data (**yes** or **no**)
- **Resolutions**: a list of resolutions (in arc seconds) in which the data will be generated
- **Timesteps**: a list of timesteps for which the data will be generated
4. If the user makes custom changes to historical input data in Excel files, the script `combine_national_data.py` should be run before generating the gridded exposure dataset.
5. National timeseries can be visualized in graphs, which can be regenerated with `country_graphs.py`

### UC1 France - 2010 Xynthia flood and windstorm

To be added.

## How to contribute
We welcome contributions to improve this project! Here are some ways you can help: <br/>
<b>Report Bugs</b>: If you find a bug, please open an issue with detailed information about the problem and how to reproduce it. <br/>
<b>Submit Pull Requests</b>: If you want to fix a bug or implement a feature, follow these steps:
<ol>
<li>Fork the repository.</li>
<li>Create a new branch (git checkout -b feature/YourFeatureName).</li>
<li>Make your changes.</li>
<li>Commit your changes (git commit -m 'Add some feature').</li>
<li>Push to the branch (git push origin feature/YourFeatureName).</li>
<li>Open a pull request. Suggest Features: Have an idea for a new feature? Open an issue to discuss it.</li>
</ol>

## Acknowledgements
<img src="https://naturalhazards.eu/eu.png" alt="EU_logo" style="max-width: 100%;">

The COMPASS project has received funding from the European Union’s HORIZON Research and Innovation Actions Programme under Grant Agreement No. 101135481

Funded by the European Union. Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or of the European Health and Digital Executive Agency (HADEA). Neither the European Union nor the granting authority HADEA can be held responsible for them.
