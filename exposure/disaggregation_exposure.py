import pandas as pd
import numpy as np
import rasterio
import geopandas as gp
from exposure_functions import (write_empty_raster, load_country_mask, save_raster_data,
                                load_ghsl_data)

## PARAMETERS
Harmonize = 'yes'
Last_hist_year = 2022 # last year of historical data
Compass_path = 'C:/HANZE2_products/Compass_exposure/'
Raster_path = 'C:/HANZE2_temp/'

# Define timespans
Years_all = list(range(1850,2101))
Years_hist = np.arange(1850,Last_hist_year+1)
Years_hist_ssp = np.arange(1850,2021)
Year_ssp_harm = list(range(Last_hist_year+1,2101))
Year_ssp_noharm = list(range(2021,2101))
Year_ghsl = np.arange(1975,2035,5)

# Load national exposure data
Pop_data = dict()
GDP_data = dict()
FA_data = dict()
Years_select = Years_hist if Harmonize == 'yes' else Years_hist_ssp
for s in np.arange(0,5):
    Pop_data[s] = pd.read_csv(Compass_path + 'Pop_combined_SSP' + str(s + 1) + '_' + Harmonize + '.csv',
                              index_col='ISOn')
    GDP_data[s] = pd.read_csv(Compass_path + 'GDP_combined_SSP' + str(s + 1) + '_' + Harmonize + '.csv',
                              index_col='ISOn')
    FA_data[s] = pd.read_csv(Compass_path + 'FA_combined_SSP' + str(s + 1) + '_' + Harmonize + '.csv',
                              index_col='ISOn')

# Load administrative map
country_dataset = rasterio.open(Compass_path + 'OSM_country_map.tif')
country_vector = gp.read_file('C:/HANZE2_rawdata/Admin/Global_OSM_boundaries_2024_v4.shp')

# load one of the GHSL dataset to get the raster profile
ghsl_dataset = rasterio.open(Raster_path + 'GHSL/GHS_POP_E1975_GLOBE_R2023A_4326_30ss_V1_0.tif')

# test
hyde_dataset = rasterio.open(Raster_path + 'HYDE/zip/popc_1980AD.asc') # offset: left: 1 top: 108 right: 1 bottom: 198

# create disaggregation
dims = [country_dataset.height, country_dataset.width]
for year in Years_all[127:128]:
    print(str(year))

    # define if year is in historical period or SSP period
    scenarios = 1 if year in Years_select else 5

    # Write empty output rasters for filling data
    for s in np.arange(0, scenarios):
        suffix = str(year) + '_SSP' + str(s + 1) + '.tif' if scenarios == 5 else str(year) + '.tif'
        write_empty_raster(ghsl_dataset.profile, Compass_path + 'Pop_' + suffix, dims)
        write_empty_raster(ghsl_dataset.profile, Compass_path + 'GDP_' + suffix, dims)
        write_empty_raster(ghsl_dataset.profile, Compass_path + 'FA_' + suffix, dims)

    # Iterate by country
    for c in Pop_data[1].index:
        print(Pop_data[1]['ISO3'][c])

        if Pop_data[1][str(year)][c] == 0:
            continue

        # Load data by country
        country_mask, location = load_country_mask(country_vector, c, country_dataset)
        ghsl_pop_year, ghsl_bld_year = load_ghsl_data(year, Year_ghsl, Raster_path, location, country_mask)

        # sum all gridded population and buildup in the raster
        ghsl_pop_year_total = ghsl_pop_year.sum()
        ghsl_bld_year_total = ghsl_bld_year.sum()

        for s in np.arange(0, scenarios):
            suffix = str(year) + '_SSP' + str(s + 1) + '.tif' if scenarios == 5 else str(year) + '.tif'
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
            # save results into the output raster
            save_raster_data(Compass_path + 'Pop_' + suffix, location, country_mask, Pop_country_raster)
            save_raster_data(Compass_path + 'GDP_' + suffix, location, country_mask, GDP_country_raster)
            save_raster_data(Compass_path + 'FA_' + suffix, location, country_mask, FA_country_raster)

        a=1