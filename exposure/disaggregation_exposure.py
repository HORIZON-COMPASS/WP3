import pandas as pd
import numpy as np
import geopandas as gp
import rasterio, sys
from exposure_functions import (write_empty_raster, load_country_mask, save_raster_data, load_ghsl_data, load_hyde_data,
                                 load_ssp_data, copy_empty, disaggregate_subnational_GDP, define_main_path)

## USER-DEFINED PARAMETERS
Harmonize = 'yes' # 'yes' or 'no'
Resolutions = [30, 1800] # has to be in arc seconds and multiplier of 30 arc seconds
Timesteps = list(range(1850,2101)) # has to be a list of timesteps

## Data availability
Last_hist_year = 2023 # last year of historical data

## Check if correct resolution was inserted
for r in Resolutions:
    if np.mod(r,30)!=0:
        sys.exit('Incorrect resolution inserted. Has to be a multiplier of 30 arc seconds')

## Paths to input and output data
MAIN_PATH = define_main_path()
Inputs_path = MAIN_PATH + 'Inputs/'
Outputs_path = MAIN_PATH + 'Outputs/'

# Define timespans
Years_hist = np.arange(1850,Last_hist_year+1)
Years_hist_ssp = np.arange(1850,2021)
Years_ghsl = np.arange(1975, 2035, 5) if Harmonize == 'yes' else np.arange(1975, 2025, 5)
Years_hyde = np.arange(1850, 1990, 10)
Years_ssp = np.arange(2030, 2105, 5) if Harmonize == 'yes' else np.arange(2020, 2105, 5)
Years_select = Years_hist if Harmonize == 'yes' else Years_hist_ssp

# Load national exposure data
Pop_data = dict()
GDP_data = dict()
FA_data = dict()
Harmonize_suffix = '_harmonized' if Harmonize == 'yes' else '_not_harm'
for s in np.arange(0,5):
    Pop_data[s] = pd.read_csv(Outputs_path + 'National_timeseries/Pop_combined_SSP' + str(s + 1) + Harmonize_suffix + '.csv',
                              index_col='ISOn')
    GDP_data[s] = pd.read_csv(Outputs_path + 'National_timeseries/GDP_combined_SSP' + str(s + 1) + Harmonize_suffix + '.csv',
                              index_col='ISOn')
    FA_data[s] = pd.read_csv(Outputs_path + 'National_timeseries/FA_combined_SSP' + str(s + 1) + Harmonize_suffix + '.csv',
                              index_col='ISOn')

# Load subnational GDP per capita
GDP_regio = pd.read_csv(Outputs_path + 'National_timeseries/GDPpc_subnational.csv')
Regio_coverage = np.unique(GDP_regio['Country'].values)

# Load administrative maps
country_dataset = rasterio.open(Inputs_path + 'Admin/OSM_country_map.tif')
subnational_dataset = rasterio.open(Inputs_path + 'Admin/OSM_subnational_map.tif')
country_vector = gp.read_file(Inputs_path + 'Admin/Global_OSM_boundaries_2024_v4.shp')

# prepare empty rasters
ghsl_dataset = rasterio.open(Inputs_path + 'GHSL/GHS_POP_E1975_GLOBE_R2023A_4326_30ss_V1_0.tif')
base_profile = ghsl_dataset.profile
for r in Resolutions:
    empty_file = Inputs_path + 'Admin/Empty_raster_'+str(r)+'.tif'
    write_empty_raster(base_profile, empty_file, r)

# create disaggregation
for year in Timesteps:
    print(str(year))
    if year > 2020:
        end_suffix = Harmonize_suffix + '.tif'
    else:
        end_suffix = '.tif'

    # define if year is in historical period or SSP period
    scenarios = 1 if year in Years_select else 5

    # Write empty output rasters for filling data
    for s in np.arange(0, scenarios):
        for r in Resolutions:
            empty_raster = Inputs_path + 'Admin/Empty_raster_' + str(r) + '.tif'
            base_suffix = str(year) + '_' + str(r)
            suffix = base_suffix + '_SSP' + str(s + 1) + end_suffix if scenarios == 5 else base_suffix + end_suffix
            copy_empty(empty_raster, Outputs_path, suffix)

    # Iterate by country
    for c in Pop_data[0].index:
        print(Pop_data[0]['ISO3'][c])

        if Pop_data[0][str(year)][c] == 0:
            continue

        # Load data by country
        country_mask, location = load_country_mask(country_vector, c, country_dataset)
        ghsl_pop_year, ghsl_bld_year = load_ghsl_data(year, Years_ghsl, Inputs_path, location, country_mask)
        if year < 1975:
            # HYDE data and correction
            hyde_pop_year, hyde_pop_base = load_hyde_data(year, Years_hyde, Inputs_path, location, country_mask)
            hyde_pop_base_total = hyde_pop_base.sum() / 100
            if hyde_pop_base_total > 0:
                hyde_pop_year_total = hyde_pop_year.sum() / 100
                hyde_ix = hyde_pop_base > 0
                hyde_factor = np.ones([country_mask.shape[0],country_mask.shape[1]])
                hyde_factor[hyde_ix] = hyde_pop_year[hyde_ix] / hyde_pop_base[hyde_ix]
                hyde_factor[~hyde_ix] = hyde_pop_year_total / hyde_pop_base_total
                ghsl_pop_year = ghsl_pop_year * hyde_factor
                ghsl_bld_year = ghsl_bld_year * hyde_factor

        for s in np.arange(0, scenarios):
            if year > Years_ssp[0]:
                # Wang SSP data
                ssp_pop_year, ssp_pop_base = load_ssp_data(year, Years_ssp, Inputs_path, location, country_mask, s)
                ssp_pop_base_total = ssp_pop_base.sum() / 100
                if ssp_pop_base_total > 0:
                    ssp_pop_year_total = ssp_pop_year.sum() / 100
                    ssp_ix = ssp_pop_base > 0
                    ssp_factor = np.ones([country_mask.shape[0], country_mask.shape[1]])
                    ssp_factor[ssp_ix] = ssp_pop_year[ssp_ix] / ssp_pop_base[ssp_ix]
                    ssp_factor[~ssp_ix] = ssp_pop_year_total / ssp_pop_base_total
                    ghsl_pop_year = ghsl_pop_year * ssp_factor
                    ghsl_bld_year = ghsl_bld_year * ssp_factor

            # sum all gridded population and buildup in the raster
            ghsl_pop_year_total = ghsl_pop_year.sum()
            ghsl_bld_year_total = ghsl_bld_year.sum()

            # correct raster values according to national population data
            Pop_adjustment = (Pop_data[s][str(year)][c] * 1000) / ghsl_pop_year_total
            Pop_country_raster = ghsl_pop_year * Pop_adjustment
            # compute subnational GDP distribution (if such data are available)
            GDP_data_s_c_y = GDP_data[s][str(year)][c]
            FA_data_s_c_y = FA_data[s][str(year)][c]
            GDPpc_data_s_c_y = GDP_data_s_c_y / Pop_data[s][str(year)][c] * 1E9
            if c in Regio_coverage:
                GDP_regio_c = GDP_regio.loc[GDP_regio['Country']==c, ].set_index(['Code'])
                GDP_country_raster, FA_country_raster = disaggregate_subnational_GDP(subnational_dataset, location,
                                                                  country_mask, ghsl_pop_year, ghsl_bld_year,
                                                                  GDP_regio_c[str(year)], GDP_data_s_c_y, GDPpc_data_s_c_y,
                                                                  FA_data_s_c_y)
            else:
                # disaggregate GDP value (60% by population, 40% by buildup area)
                GDP_per_pop = GDP_data_s_c_y * 0.6 / ghsl_pop_year_total * 1E9
                GDP_per_bld = GDP_data_s_c_y * 0.4 / ghsl_bld_year_total * 1E9
                GDP_country_raster = ghsl_pop_year * GDP_per_pop + ghsl_bld_year * GDP_per_bld
                # disaggregate fixed assets by buildup area
                FA_per_bld = FA_data[s][str(year)][c] / ghsl_bld_year_total * 1E9
                FA_country_raster = ghsl_bld_year * FA_per_bld

            # adapt data for saving
            if location[2]==43201:
                location_save = location + [0,108,-1,0]
                Pop_country_raster = Pop_country_raster[:,1:]
                GDP_country_raster = GDP_country_raster[:,1:]
                FA_country_raster = FA_country_raster[:,1:]
            else:
                location_save = location + [-1,108,0,0]

            # save data and aggregate resolution if necessary
            for r in Resolutions:
                base_suffix = str(year) + '_' + str(r)
                suffix = base_suffix + '_SSP' + str(s + 1) + end_suffix if scenarios == 5 else base_suffix + end_suffix
                save_raster_data(Outputs_path + 'Population/Pop_' + suffix, location_save, Pop_country_raster, r)
                save_raster_data(Outputs_path + 'GDP/GDP_' + suffix, location_save, GDP_country_raster, r)
                save_raster_data(Outputs_path + 'Fixed_asset_value/FA_' + suffix, location_save, FA_country_raster, r)