import pandas as pd
import numpy as np
import geopandas as gp
import rasterio, sys
from exposure_functions import (write_empty_raster, load_country_mask, save_raster_data, load_ghsl_data,
                                load_hyde_data, load_ssp_data, copy_empty)

## PARAMETERS
Resolutions = [30, 1800] # has to be in arc seconds and multiplier of 30 arc seconds
Harmonize = 'yes' # 'yes' or 'no'
Last_hist_year = 2022 # last year of historical data
Compass_path = '/p/tmp/dominikp/COMPASS/Exposure/' #'C:/HANZE2_products/Compass_exposure/' #
Raster_path = '/p/tmp/dominikp/COMPASS/Exposure/' #'C:/HANZE2_temp/COMPASS_Exposure/' #
for r in Resolutions:
    if np.mod(r,30)!=0:
        sys.exit('Incorrect resolution inserted. Has to be a multiplier of 30 arc seconds')

# Define timespans
Years_all = list(range(1850,2101))
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
for s in np.arange(0,5):
    Pop_data[s] = pd.read_csv(Compass_path + 'National_data/Pop_combined_SSP' + str(s + 1) + '_' + Harmonize + '.csv',
                              index_col='ISOn')
    GDP_data[s] = pd.read_csv(Compass_path + 'National_data/GDP_combined_SSP' + str(s + 1) + '_' + Harmonize + '.csv',
                              index_col='ISOn')
    FA_data[s] = pd.read_csv(Compass_path + 'National_data/FA_combined_SSP' + str(s + 1) + '_' + Harmonize + '.csv',
                              index_col='ISOn')

# Load administrative map
country_dataset = rasterio.open(Compass_path + 'Admin/OSM_country_map.tif')
country_vector = gp.read_file(Compass_path + 'Admin/Global_OSM_boundaries_2024_v4.shp')

# prepare empty rasters
ghsl_dataset = rasterio.open(Raster_path + 'GHSL/GHS_POP_E1975_GLOBE_R2023A_4326_30ss_V1_0.tif')
base_profile = ghsl_dataset.profile
for r in Resolutions:
    empty_file = Compass_path + 'Admin/Empty_raster_'+str(r)+'.tif'
    write_empty_raster(base_profile, empty_file, r)

# create disaggregation
for year in list(range(2023,2101)): #Years_all: # #[1850, 1927, 1975, 2022, 2030, 2057, 2100]: #
    print(str(year))
    if year > 2020:
        end_suffix = '_' + Harmonize + '.tif'
    else:
        end_suffix = '.tif'

    # define if year is in historical period or SSP period
    scenarios = 1 if year in Years_select else 5

    # Write empty output rasters for filling data
    for s in np.arange(0, scenarios): #[1]: #
        for r in Resolutions:
            empty_raster = Compass_path + 'Admin/Empty_raster_' + str(r) + '.tif'
            base_suffix = str(year) + '_' + str(r)
            suffix = base_suffix + '_SSP' + str(s + 1) + end_suffix if scenarios == 5 else base_suffix + end_suffix
            copy_empty(empty_raster, Compass_path, suffix)

    # Iterate by country
    for c in Pop_data[1].index: #[242,674,242,674,492]: #
        print(Pop_data[1]['ISO3'][c])

        if Pop_data[1][str(year)][c] == 0:
            continue

        # Load data by country
        country_mask, location = load_country_mask(country_vector, c, country_dataset)
        ghsl_pop_year, ghsl_bld_year = load_ghsl_data(year, Years_ghsl, Raster_path, location, country_mask)
        if year < 1975:
            # HYDE data and correction
            hyde_pop_year, hyde_pop_base = load_hyde_data(year, Years_hyde, Raster_path, location, country_mask)
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
                ssp_pop_year, ssp_pop_base = load_ssp_data(year, Years_ssp, Raster_path, location, country_mask, s)
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
            # disaggregate GDP value (60% by population, 40% by buildup area)
            GDP_per_pop = GDP_data[s][str(year)][c] * 0.6 / ghsl_pop_year_total * 1E9
            GDP_per_bld = GDP_data[s][str(year)][c] * 0.4 / ghsl_bld_year_total * 1E9
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
                save_raster_data(Compass_path + 'Pop_' + suffix, location_save, Pop_country_raster, r)
                save_raster_data(Compass_path + 'GDP_' + suffix, location_save, GDP_country_raster, r)
                save_raster_data(Compass_path + 'FA_' + suffix, location_save, FA_country_raster, r)