import pandas as pd
import numpy as np
from exposure_functions import copula_fit_frank, prepare_fixed_asset_data, fixed_asset_estimate, define_main_path
from scipy.interpolate import interp1d

## USER-DEFINED PARAMETERS
Harmonize = 'yes' # 'yes' or 'no'

## Data availability
if Harmonize == 'yes':
    Last_hist_year_pop = 2023 # last year of historical population data
    Last_hist_year_eco = 2023 # last year of historical economic data
else:
    Last_hist_year_pop = 2020 # last year of historical population data
    Last_hist_year_eco = 2020 # last year of historical economic data
Last_hist_year_regio = 2023 # last year of historical subnational GDP per capita data
Last_weo_year = 2029 # last year for which WEO projections are available
Base_SSP_year = 2020 # base year of SSP projections

## Paths to input and output data
MAIN_PATH = define_main_path()
Inputs_path = MAIN_PATH + 'Inputs/National_data/'
Outputs_path = MAIN_PATH + 'Outputs/National_timeseries/'

## Input national timeseries historical
National_data_hist_file = Inputs_path + 'National_exposure_all.xlsx'
FA_raw = pd.read_excel(open(National_data_hist_file, 'rb'), sheet_name='Fixed_assets_to_GDP_raw', index_col='ISOn')
GDPpc_hist = pd.read_excel(open(National_data_hist_file, 'rb'), sheet_name='GDP_per_capita_2017$', index_col='ISOn')
Pop_hist = pd.read_excel(open(National_data_hist_file, 'rb'), sheet_name='Population', index_col='ISOn')
Countries = range(0,248)
Years_hist_pop = list(range(1850,Last_hist_year_pop+1))
Years_hist_eco = list(range(1850,Last_hist_year_eco+1))
Years_all = list(range(1850,2101))

## Input UN WPP2024 projections
National_data_wpp_file = Inputs_path + 'UN_PPP2024_Output_PopTot.xlsx'
Pop_wpp = pd.read_excel(open(National_data_wpp_file, 'rb'), sheet_name='Median', header=16, index_col='Location code')
Years_wpp = list(np.arange(Last_hist_year_pop+1, Last_weo_year+1))

## Input IMF WEO projections
National_data_weo_file = Inputs_path + 'WEOOct2024all.xlsx'
National_data_weo = pd.read_excel(open(National_data_weo_file, 'rb'), sheet_name='WEOOct2024all')
Years_weo = list(np.arange(Last_hist_year_eco, Last_weo_year+1))
GDPpc_weo = National_data_weo.loc[National_data_weo['Units'] == 'Purchasing power parity; 2017 international dollar',]

## Input national SSP projections
National_data_ssp_file = Inputs_path + 'SSP_3_1_main_drivers.xlsx'
National_data_ssp = pd.read_excel(open(National_data_ssp_file, 'rb'), sheet_name='Data_select')
SSP_ISO_reference = pd.read_excel(open(National_data_ssp_file, 'rb'), sheet_name='SSP_ISO_reference', index_col='ISOn')
SSPs = np.arange(1,6)
Years_ssp = np.arange(2020,2101)
Years_ssp_5yr = list(range(2020,2105,5))

## Fixed asset data gapfilling
Combined_data_dz = prepare_fixed_asset_data(FA_raw, GDPpc_hist)
copula_assets, copula_samples = copula_fit_frank(Combined_data_dz)

## combine national timeseries
Pop_combined = np.ones([5, len(Countries), len(Years_all)]) * -1
GDPpc_combined = np.ones([5, len(Countries), len(Years_all)]) * -1
GDP_combined = np.ones([5, len(Countries), len(Years_all)]) * -1
FA_combined = np.ones([5, len(Countries), len(Years_all)]) * -1
for kc, c in enumerate(Pop_hist.index):
    print(str(Pop_hist.loc[c,'Name']))

    # extract country data series for historical
    C_Pop_hist = Pop_hist.loc[c,Years_hist_pop].values
    C_GDPpc_hist = GDPpc_hist.loc[c,Years_hist_eco].values
    C_FA_raw = FA_raw.loc[c,Years_hist_eco].values

    # omit uninhabited territories
    if sum(C_Pop_hist)==0:
        Pop_combined[:, kc, :] = 0
        GDP_combined[:, kc, :] = 0
        FA_combined[:, kc, :] = 0
        continue

    # extract country data series for SSPs
    SSP_Pop_reference = SSP_ISO_reference.loc[c,'Pop']
    SSP_GDP_reference = SSP_ISO_reference.loc[c,'GDP']
    C_Pop_SSP_5yr = National_data_ssp.loc[(National_data_ssp['Region']==SSP_Pop_reference) &
                                          (National_data_ssp['Variable']=='Population') &
                                          (National_data_ssp['Scenario']!='Historical Reference'), Years_ssp_5yr]
    # change rate relative to 2020
    C_Pop_SSP = interp1d(Years_ssp_5yr,C_Pop_SSP_5yr)(Years_ssp) / C_Pop_SSP_5yr.values[0, 0] * C_Pop_hist[Base_SSP_year - 1850]
    # GDP from SSPs (OECD or IIASA projection)
    if SSP_GDP_reference=='IIASA':
        C_GDPpc_SSP_5yr = National_data_ssp.loc[(National_data_ssp['Region'] == SSP_Pop_reference) &
                                                (National_data_ssp['Variable'] == 'GDP|PPP [per capita]_IIASA'),
                                                Years_ssp_5yr[1:]]
        # change rate relative to 2020
        C_GDPpc_SSP = (interp1d(Years_ssp_5yr[1:], C_GDPpc_SSP_5yr, fill_value='extrapolate')(Years_ssp) /
                       np.mean(C_GDPpc_SSP_5yr[2025].values)) * C_GDPpc_hist[Base_SSP_year - 1850]
    else:
        C_GDPpc_SSP_5yr = National_data_ssp.loc[(National_data_ssp['Region'] == SSP_GDP_reference) &
                                                (National_data_ssp['Variable'] == 'GDP|PPP [per capita]') &
                                                (National_data_ssp['Scenario'] != 'Historical Reference'),
                                                Years_ssp_5yr]
        # change rate relative to 2020
        C_GDPpc_SSP = interp1d(Years_ssp_5yr, C_GDPpc_SSP_5yr)(Years_ssp) / C_GDPpc_SSP_5yr.values[0, 0] * C_GDPpc_hist[Base_SSP_year - 1850]

    # WEO projection, if used for harmonization
    C_GDPpc_WEO_change = np.concatenate(([1], [np.nan] * (len(Years_weo)-1)))
    C_Pop_wpp  = [np.nan] * (len(Years_wpp))
    if Harmonize == 'yes':
        # UN projection
        if c in Pop_wpp.index:
            C_Pop_wpp = Pop_wpp.loc[c, Years_wpp].values

        # WEO projection
        C_ISO3 = Pop_hist.loc[c,'ISO3']
        if C_ISO3 == 'PSE':
            C_ISO3 = 'WBG'
        elif C_ISO3 == 'XKX':
            C_ISO3 = 'UVK'
        ixc = GDPpc_weo['ISO'] == C_ISO3
        # check if WEO projection available
        if sum(ixc)>0:
            C_GDPpc_WEO = GDPpc_weo.loc[ixc, Years_weo].values[0]
            C_GDPpc_WEO_change = C_GDPpc_WEO / C_GDPpc_WEO[0]

    # Combine historical, WEO and SSP data
    for s in range(0,5):
        hist_column_pop = len(Years_hist_pop)
        hist_column_eco = len(Years_hist_eco)
        # historical data
        Pop_combined[s, kc, :hist_column_pop] = C_Pop_hist
        GDPpc_combined[s, kc, :hist_column_eco] = C_GDPpc_hist

        # Add UN and WEO projections for harmonization, if enabled
        Pop_combined[s, kc, hist_column_pop:hist_column_pop+len(Years_wpp)] = C_Pop_wpp
        C_GDPpc_WEO_harm = C_GDPpc_hist[hist_column_eco-1] * C_GDPpc_WEO_change
        GDPpc_combined[s, kc, hist_column_eco-1:hist_column_eco+len(Years_weo)-1] = C_GDPpc_WEO_harm

        # SSP population
        Data_avail_pop = sum(Pop_combined[s, kc, :] >= 0)
        SSP_Pop_diff = Pop_combined[s, kc, Data_avail_pop-1] / C_Pop_SSP[s, Data_avail_pop-171]
        SSP_Pop_offset = interp1d([Data_avail_pop + 1849, 2100], [SSP_Pop_diff, 1])(
                            Years_ssp[Data_avail_pop - 171:])
        Pop_combined[s, kc, Data_avail_pop-1:] = C_Pop_SSP[s, Data_avail_pop-171:] * SSP_Pop_offset

        # SSP GDP
        Data_avail_GDP = sum(GDPpc_combined[s, kc, :] >= 0)
        SSP_GDP_diff = GDPpc_combined[s, kc, Data_avail_GDP - 1] / C_GDPpc_SSP[s, Data_avail_GDP - 171]
        SSP_GDP_offset = interp1d([Data_avail_GDP + 1849, 2100], [SSP_GDP_diff, 1])(
                            Years_ssp[Data_avail_GDP - 171:])
        GDPpc_combined[s, kc, Data_avail_GDP - 1:] = C_GDPpc_SSP[s, Data_avail_GDP - 171:] * SSP_GDP_offset

        # Fixed assets
        GDPpc_combined_c_s = GDPpc_combined[s, kc, :]
        C_FA_estimate = fixed_asset_estimate(C_FA_raw, copula_assets, copula_samples, GDPpc_combined_c_s, Years_all)
        GDP_combined[s, kc, :] = GDPpc_combined[s, kc, :] * Pop_combined[s, kc, :] / 1E6
        FA_combined[s, kc, :] = GDP_combined[s, kc, :] * C_FA_estimate

# save timeseries
Harmonize_suffix = '_harmonized' if Harmonize == 'yes' else '_not_harm'
for s in range(0,5):
    Pop_combined_df = pd.DataFrame(data=Pop_combined[s, :, :], columns=Years_all,index=Pop_hist.index)
    Pop_combined_dff = pd.concat([Pop_hist[['ISO3']], Pop_combined_df], axis=1)
    Pop_combined_dff.to_csv(Outputs_path + 'Pop_combined_SSP' + str(s + 1) + Harmonize_suffix + '.csv', sep=',')
    GDP_combined_df = pd.DataFrame(data=GDP_combined[s, :, :], columns=Years_all,index=Pop_hist.index)
    GDP_combined_dff = pd.concat([Pop_hist[['ISO3']], GDP_combined_df], axis=1)
    GDP_combined_dff.to_csv(Outputs_path + 'GDP_combined_SSP' + str(s + 1) + Harmonize_suffix + '.csv', sep=',')
    FA_combined_df = pd.DataFrame(data=FA_combined[s, :, :], columns=Years_all,index=Pop_hist.index)
    FA_combined_dff = pd.concat([Pop_hist[['ISO3']], FA_combined_df], axis=1)
    FA_combined_dff.to_csv(Outputs_path + 'FA_combined_SSP' + str(s + 1) + Harmonize_suffix + '.csv', sep=',')

### SUBNATIONAL DATA INTEGRATION
## Input subnational GDP per capita
GDPpc_regio = pd.read_excel(open(Inputs_path + 'Subnational_exposure_all.xlsx', 'rb'),
                            sheet_name='GDP_pc')
Years_hist_regio = list(range(1850, Last_hist_year_regio + 1))
Years_hist_regio_n = np.array(range(1850, Last_hist_year_regio + 1))

## gapfill subnational
GDPpc_subnational = np.ones([len(GDPpc_regio.Code), len(Years_all)]) * -1
for kr, r in enumerate(GDPpc_regio.index):
    R_GDPpc = GDPpc_regio.values[kr, 5:].astype('float')
    ixr = np.invert(np.isnan(R_GDPpc))
    R_data = R_GDPpc[ixr]
    GDPpc_subnational[kr, :] = interp1d(Years_hist_regio_n[ixr], R_data, bounds_error=False,
                                        kind='linear', fill_value=(R_data[0], R_data[-1]))(Years_all)

## save subnational data
Regio_combined_df = pd.DataFrame(data=GDPpc_subnational, columns=Years_all)
Regio_combined_dff = pd.concat([GDPpc_regio[['Code', 'Country', 'Name']], Regio_combined_df], axis=1)
Regio_combined_dff.to_csv(Outputs_path + 'GDPpc_subnational.csv', sep=',')