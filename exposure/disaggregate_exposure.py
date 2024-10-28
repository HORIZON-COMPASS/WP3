import pandas as pd
import numpy as np
from exposure_functions import copula_inference_Frank, copula_fit_frank, prepare_fixed_asset_data
from scipy.interpolate import interp1d

## PARAMETRS
Harmonize = 'yes'


## Input national timeseries historical
National_data_hist_file = 'C:/HANZE2_products/Compass_exposure/National_exposure_all.xlsx'
Fixed_asset_raw = pd.read_excel(open(National_data_hist_file, 'rb'), sheet_name='Fixed_assets_to_GDP_raw', index_col='ISOn')
GDPpc_hist = pd.read_excel(open(National_data_hist_file, 'rb'), sheet_name='GDP_per_capita_2017$', index_col='ISOn')
Pop_hist = pd.read_excel(open(National_data_hist_file, 'rb'), sheet_name='Population', index_col='ISOn')
Countries = range(0,248)
Years_hist = list(range(1850,2023))

## Input IMF WEO projections
National_data_weo_file = 'C:/HANZE2_products/Compass_exposure/WEOOct2024all.xlsx'
National_data_weo = pd.read_excel(open(National_data_weo_file, 'rb'), sheet_name='WEOOct2024all')
Years_weo = list(np.arange(2022,2030))
GDPpc_weo = National_data_weo.loc[National_data_weo['Units'] == 'Purchasing power parity; 2017 international dollar',]

## Input national SSP projections
National_data_ssp_file = 'C:/HANZE2_products/Compass_exposure/SSP_3_1_main_drivers.xlsx'
National_data_ssp = pd.read_excel(open(National_data_ssp_file, 'rb'), sheet_name='Data_select')
SSP_ISO_reference = pd.read_excel(open(National_data_ssp_file, 'rb'), sheet_name='SSP_ISO_reference', index_col='ISOn')
SSPs = np.arange(1,6)
Years_ssp = np.arange(2023,2101)
Years_ssp_5yr = list(range(2020,2105,5))

# ## Fixed asset data gapfilling
# Combined_data_dz = prepare_fixed_asset_data(Fixed_asset_raw, GDPpc_hist)
# copula_assets, copula_samples = copula_fit_frank(Combined_data_dz)

## combine national timeseries
Pop_combined = np.zeros([5, len(Countries), len(range(1850,2101))])
GDPpc_combined = np.zeros([5, len(Countries), len(range(1850,2101))])
Fixed_asset_combined = np.zeros([5, len(Countries), len(range(1850,2101))])
for c in Pop_hist.index:
    print(str(c))

    # extract country data series for historical
    C_Pop_hist = Pop_hist.loc[c,Years_hist].values
    C_GDPpc_hist = GDPpc_hist.loc[c,Years_hist].values
    C_Fixed_asset_raw = Fixed_asset_raw.loc[c,Years_hist].values

    # extract country data series for SSPs
    SSP_Pop_reference = SSP_ISO_reference.loc[c,'Pop']
    SSP_GDP_reference = SSP_ISO_reference.loc[c,'GDP']
    C_Pop_SSP_5yr = National_data_ssp.loc[(National_data_ssp['Region']==SSP_Pop_reference) &
                                          (National_data_ssp['Variable']=='Population') &
                                          (National_data_ssp['Scenario']!='Historical Reference'), Years_ssp_5yr]
    # change rate relative to 2020
    C_Pop_SSP = interp1d(Years_ssp_5yr,C_Pop_SSP_5yr)(Years_ssp) / C_Pop_SSP_5yr.values[0, 0]
    # GDP from SSPs (OECD or IIASA projection)
    if SSP_GDP_reference=='IIASA':
        C_GDPpc_SSP_5yr = National_data_ssp.loc[(National_data_ssp['Region'] == SSP_Pop_reference) &
                                                (National_data_ssp['Variable'] == 'GDP|PPP [per capita]_IIASA'),
                                                Years_ssp_5yr[1:]]
        # change rate relative to 2020
        C_GDPpc_SSP = (interp1d(Years_ssp_5yr[1:], C_GDPpc_SSP_5yr, fill_value='extrapolate')(Years_ssp) /
                       np.mean(C_GDPpc_SSP_5yr[2025].values))
    else:
        C_GDPpc_SSP_5yr = National_data_ssp.loc[(National_data_ssp['Region'] == SSP_GDP_reference) &
                                                (National_data_ssp['Variable'] == 'GDP|PPP [per capita]') &
                                                (National_data_ssp['Scenario'] != 'Historical Reference'),
                                                Years_ssp_5yr]
        # change rate relative to 2020
        C_GDPpc_SSP = interp1d(Years_ssp_5yr, C_GDPpc_SSP_5yr)(Years_ssp) / C_GDPpc_SSP_5yr.values[0, 0]

    # WEO projection
    C_ISO3 = Pop_hist.loc[c,'ISO3']
    if C_ISO3 == 'PSE':
        C_ISO3 = 'WBG'
    elif C_ISO3 == 'XKX':
        C_ISO3 = 'UVK'
    C_GDPpc_WEO = GDPpc_weo.loc[GDPpc_weo['ISO'] == C_ISO3, Years_weo].values

    a=1