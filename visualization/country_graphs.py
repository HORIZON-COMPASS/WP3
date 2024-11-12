import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

## PARAMETERS
Resolutions = [30, 1800] # has to be in arc seconds and multiplier of 30 arc seconds
Harmonize = 'yes' # 'yes' or 'no'
Last_hist_year = 2022 # last year of historical data
Compass_path = 'C:/HANZE2_products/Compass_exposure/' #
Raster_path = 'C:/HANZE2_temp/COMPASS_Exposure/' #

# Define timespans
Years_all = list(range(1850,2101))
Years_hist = np.arange(1850, Last_hist_year+1) if Harmonize == 'yes' else np.arange(1850, 2021)
Years_ssp = np.arange(Last_hist_year+1, 2101) if Harmonize == 'yes' else np.arange(2021, 2101)

# Load national exposure data
Pop_data = dict()
GDP_data = dict()
FA_data = dict()
for s in np.arange(0,5):
    Pop_data[s] = pd.read_csv(Compass_path + 'National_data/Pop_combined_SSP' + str(s + 1) + '_' + Harmonize + '.csv',
                              index_col='ISOn')
    GDP_data[s] = pd.read_csv(Compass_path + 'National_data/GDP_combined_SSP' + str(s + 1) + '_' + Harmonize + '.csv',
                              index_col='ISOn')
    FA_data[s] = pd.read_csv(Compass_path + 'National_data/FA_combined_SSP' + str(s + 1) + '_' + Harmonize + '.csv',
                              index_col='ISOn')
Pop_hist = pd.read_excel(open(Compass_path + 'National_data/National_exposure_all.xlsx', 'rb'),
                         sheet_name='Population', index_col='ISOn')

# Graph information
titles = ['Population (million)', 'GDP per capita (thsd. 2017$ PPP)', 'GDP (billion 2017$ PPP)',
          'Fixed assets to GDP ratio (%)', 'Fixed assets stock (billion 2017$ PPP)']
titles2 = ['Population change (%)', 'GDP per capita change (%)', 'GDP change (%)',
          'Fixed assets to GDP ratio change (%)', 'Fixed assets stock change (%)']
ssp_colors = ["tab:green", "tab:blue",  "tab:red", "tab:orange", "tab:pink"]

# Iterate by country
Columns = Pop_data[0].columns[1:]
Columns_ssp = Pop_data[0].columns[1+len(Years_hist):]
for c in Pop_data[0].index:
    country_name = Pop_hist.loc[c,'Name']

    fig, axs = plt.subplots(2, 5, constrained_layout=True, figsize=(20, 8))
    fig.suptitle(country_name, fontsize=14)
    for p in np.arange(0, 5):
        for s in np.arange(0, 5):
            if p == 0: # population
                data_all = Pop_data[s].loc[c, Columns].values / 1000
            elif p == 1: # GDP per capita
                data_all = GDP_data[s].loc[c, Columns].values / Pop_data[s].loc[c, Columns].values * 1000
            elif p == 2: # GDP
                data_all = GDP_data[s].loc[c, Columns].values
            elif p == 3: # Fixed assets to GDP
                data_all = FA_data[s].loc[c, Columns].values / GDP_data[s].loc[c, Columns].values * 100
            else:
                data_all = FA_data[s].loc[c, Columns].values  # Fixed assets
            if s==0:
                axs[0, p].plot(Years_hist, data_all[:len(Years_hist)], label="Historical", c='black')
                axs[1, p].plot(Years_hist[1:], (data_all[1:len(Years_hist)] / data_all[:len(Years_hist)-1] -1) * 100,
                               label="Historical", c='black')
            axs[0, p].plot(Years_ssp, data_all[len(Years_hist):], label="SSP"+str(s+1), c=ssp_colors[s])
            axs[1, p].plot(Years_ssp, (data_all[len(Years_hist):] / data_all[len(Years_hist)-1:-1]-1) * 100,
                           label="SSP" + str(s + 1), c=ssp_colors[s])

        axs[0, p].set_title(titles[p])
        axs[1, p].set_title(titles2[p])
        for p in [1,2,4]:
            axs[0, p].set_yscale('log')

    axs[0, 1].legend()

    plt.savefig(Raster_path  + 'Figures/InputData_'+ country_name +'.png', dpi=200)
    plt.close(fig)