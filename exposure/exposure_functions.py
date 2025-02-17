import numpy as np
import rasterio, os, shutil
from copulas.bivariate import Frank
from rasterio import Affine
from rasterio.windows import Window
from scipy.stats import rankdata
from scipy.ndimage import zoom

def prepare_fixed_asset_data(Fixed_asset_raw, GDPpc):

    Select_years = [3, 13, 23, 33, 43, 53, 66, 73, 82, 91, 103, 113, 123, 133, 143, 153, 163, 172]
    Fixed_asset_raw_a = Fixed_asset_raw.values[:, Select_years].astype(float)
    Fixed_asset_raw_av = Fixed_asset_raw_a.reshape(-1, 1)

    GDPpc_a = GDPpc.values[:, Select_years].astype(float)
    GDPpc_av = GDPpc_a.reshape(-1, 1)

    Combined_data = np.concatenate([GDPpc_av, Fixed_asset_raw_av], axis=1)
    Combined_data_d = Combined_data[~np.isnan(Combined_data).any(axis=1)]
    ix = (Combined_data_d > 0) & (Combined_data_d < 10)
    Combined_data_dz = Combined_data_d[ix.any(axis=1)]

    return Combined_data_dz

### Fit Frank copula to the data
def copula_fit_frank(Combined_data_dz):
    Combined_data_ranked = rankdata(Combined_data_dz, method='min', axis=0) / (Combined_data_dz.shape[0] + 1)
    copula = Frank()
    copula.fit(Combined_data_ranked)
    param = copula.theta
    X_margins = np.sort(np.stack([Combined_data_ranked[:, 0], Combined_data_dz[:, 0]], axis=1), axis=0)
    Y_margins = np.sort(np.stack([Combined_data_ranked[:, 1], Combined_data_dz[:, 1]], axis=1), axis=0)
    copula_assets = [param, X_margins, Y_margins]
    rng = np.random.default_rng(12345)
    copula_samples = rng.uniform(low=0, high=1, size=10000)

    return copula_assets, copula_samples

## Inference with Frank copula
def copula_inference_Frank(copula,u,v):

    theta = copula[0]
    X = copula[1]
    Y = copula[2]

    V = np.interp(v, X[:,1], X[:,0])

    a = -(1 / theta)
    b = 1 - np.exp( - theta)
    c = u ** -1 - 1
    d = np.exp( -theta * V)
    f = a * np.log( 1 - b / (c * d +1 ))
    f[f>1]=1
    sp = np.interp(f, Y[:,0], Y[:,1])

    return sp

def fixed_asset_estimate(Fixed_asset_orig, copula_assets, copula_samples, GDPpc_all, Years):

    Fixed_asset_raw = np.concatenate([Fixed_asset_orig,[np.nan] * (len(Years)-len(Fixed_asset_orig))])
    Fixed_asset_pred = np.zeros([len(Years)])
    Fixed_asset_pred_c = np.zeros([len(Years)])
    for y in Years:
        GDPpc_cy = GDPpc_all[y-1850]
        Fixed_asset_pred_c[y-1850] = np.mean(copula_inference_Frank(copula_assets, copula_samples, GDPpc_cy))
    asset_avail = ~np.isnan(Fixed_asset_raw.astype('float64'))
    if sum(asset_avail)==0:
        Fixed_asset_pred = Fixed_asset_pred_c
    else:
        Fixed_asset_pred[asset_avail] = Fixed_asset_raw[asset_avail]
        Index_first = np.where(asset_avail == 1)[0][0]
        Index_last = np.where(asset_avail == 1)[0][-1]
        Fixed_asset_first = Fixed_asset_raw[Index_first]
        Fixed_asset_last = Fixed_asset_raw[Index_last]
        Fixed_asset_pred[0:Index_first] = Fixed_asset_pred_c[0:Index_first] * Fixed_asset_first / Fixed_asset_pred_c[Index_first]
        Fixed_asset_pred[Index_last:] = Fixed_asset_pred_c[Index_last:] * Fixed_asset_last / Fixed_asset_pred_c[Index_last]

    Fixed_asset_pred[np.isnan(Fixed_asset_pred)] = 0

    return Fixed_asset_pred

def write_empty_raster(output_profile, full_filename, resolution):

    # adapt profile
    R = resolution / 30
    output_profile.data['dtype'] = 'float32'
    output_profile.data['width'] = int(43200 / R)
    output_profile.data['height'] = int(21600 / R)
    output_profile.data['transform'] = Affine(R / 120, 0, -180, 0, -R / 120, 90)

    dimensions = [output_profile.data['height'], output_profile.data['width']]

    if os.path.isfile(full_filename):
        #
        print(full_filename + " already exists")
    else:
        empty_data = np.zeros(dimensions, dtype = np.float32)
        with rasterio.Env():
            with rasterio.open(full_filename, 'w', **output_profile) as dst:
                dst.write(empty_data, 1)

def copy_empty(empty_raster, Compass_path, suffix):

    vars = ['Outputs/Population/Pop_', 'Outputs/GDP/GDP_', 'Outputs/Fixed_asset_value/FA_']

    for v in vars:
        full_filename = Compass_path + v + suffix
        if os.path.isfile(full_filename):
            os.remove(full_filename)
        shutil.copy(empty_raster, full_filename)

def load_country_mask(country_vector, c, country_dataset):

    country_vector_sel = country_vector.loc[country_vector['ISOnum']==c,]
    EXT_MIN_X = country_vector_sel['EXT_MIN_X'].values - country_dataset.bounds.left
    EXT_MAX_X = country_vector_sel['EXT_MAX_X'].values - country_dataset.bounds.left
    EXT_MIN_Y = country_vector_sel['EXT_MIN_Y'].values - country_dataset.bounds.bottom
    EXT_MAX_Y = country_vector_sel['EXT_MAX_Y'].values - country_dataset.bounds.bottom

    # find the country in the raster
    res = country_dataset.res[0]
    start_grid_x = np.floor(EXT_MIN_X / res)
    start_grid_y = np.floor(country_dataset.shape[0] - EXT_MAX_Y / res)
    extent_x = np.ceil((EXT_MAX_X - EXT_MIN_X) / res)
    extent_y = np.ceil((EXT_MAX_Y - EXT_MIN_Y) / res) + 1
    location = np.concatenate([start_grid_x, start_grid_y, extent_x, extent_y])
    country = country_dataset.read(1, window=Window(start_grid_x, start_grid_y, extent_x, extent_y))
    # find grid cells specific for the country
    country_mask = country == c

    return country_mask, location

# helper for loading and masking raster for a NUTS region
def load_dataset_by_country(dataset, location, country_mask):

    col_off = location[0]
    row_off = location[1]
    width = location[2]
    height = location[3]

    read_dataset = dataset.read(1, window=Window(col_off, row_off, width, height))
    read_dataset[~country_mask] = 0
    read_dataset[read_dataset < 0] = 0

    return read_dataset

def aggregate_data(data, location, r):

    if r == 30:
        data_r = data
        location_r = location
    else:
        factor = r / 30
        col_off = np.divmod(location[0], factor)
        row_off = np.divmod(location[1], factor)
        width = np.divmod(location[2] + col_off[1], factor)[0] + 1 if location[2] < 43200 else 43200 / factor
        height = np.divmod(location[3] + row_off[1], factor)[0] + 1
        data_z = np.zeros([int((height) * factor), int((width) * factor)])
        data_z[int(row_off[1]):int(row_off[1]+location[3]), int(col_off[1]):int(col_off[1]+location[2])] = data
        # Target dimensions
        target_shape = (int(height), int(width))
        # Reshape to create blocks and then sum
        block_shape = (data_z.shape[0] // target_shape[0], data_z.shape[1] // target_shape[1])
        data_r = data_z.reshape(target_shape[0], block_shape[0], target_shape[1], block_shape[1]).sum(axis=(1, 3))
        location_r = np.array([col_off[0], row_off[0], target_shape[1], target_shape[0]])

    return data_r, location_r

def save_raster_data(path_and_name, location_o, raster_dataset_o, r):

    # aggregate data if necessary
    raster_dataset, location = aggregate_data(raster_dataset_o, location_o, r)

    col_off = location[0]
    row_off = location[1]
    width = location[2]
    height = location[3]

    raster_dataset_year = rasterio.open(path_and_name)
    read_dataset_year = raster_dataset_year.read(1, window=Window(col_off, row_off, width, height))
    read_dataset_year += raster_dataset
    profile = raster_dataset_year.profile
    raster_dataset_year.close()
    with rasterio.open(path_and_name, 'r+', **profile) as dst:
        dst.write(read_dataset_year, window=Window(col_off, row_off, width, height), indexes=1)
    raster_dataset_year.close()

def load_ghsl_data(year, Year_ghsl, Raster_path, location, country_mask):

    year_h = ''
    ghsl_pop_dataset_h = ''
    ghsl_bld_dataset_h = ''
    interp = 0
    ghsl_version = '_GLOBE_R2023A_4326_30ss_V1_0.tif'
    ghsl_first_year = Year_ghsl[0]
    ghsl_end_year = Year_ghsl[-1]

    location_ghsl_pop = location + [0, 0, 0, 0]
    location_ghsl_bld = location + [-1, 0, 0, 0]
    # correct for offset in the build surface dataset
    country_mask_bld = country_mask[:, 1:] if country_mask.shape[1] >= 43200 else country_mask

    if (year > ghsl_first_year) & (year < ghsl_end_year) & (year not in Year_ghsl):
        # if year is between GHSL dataset, open upper limit dataset for interpolation
        interp = 1
        year_l = max(Year_ghsl[Year_ghsl < year])
        year_h = min(Year_ghsl[Year_ghsl > year])
        ghsl_pop_dataset_h = rasterio.open(Raster_path + 'GHSL/GHS_POP_E' + str(year_h) + ghsl_version)
        ghsl_bld_dataset_h = rasterio.open(Raster_path + 'GHSL/GHS_BUILT_S_E' + str(year_h) + ghsl_version)
    elif year <= ghsl_first_year:
        # Use 1975 dataset for 1850-1975
        year_l = ghsl_first_year
    elif year >= ghsl_end_year:
        # Use 2030 dataset for 2030-2100
        year_l = ghsl_end_year
    else:
        year_l = year
    # open GHSL dataset or its lower limit for interpolation
    ghsl_pop_dataset = rasterio.open(Raster_path + 'GHSL/GHS_POP_E' + str(year_l) + ghsl_version)
    ghsl_bld_dataset = rasterio.open(Raster_path + 'GHSL/GHS_BUILT_S_E' + str(year_l) + ghsl_version)

    if interp == 1:
        ghsl_pop_year_l = load_dataset_by_country(ghsl_pop_dataset, location_ghsl_pop, country_mask)
        ghsl_bld_year_l = load_dataset_by_country(ghsl_bld_dataset, location_ghsl_bld, country_mask_bld)
        ghsl_pop_year_h = load_dataset_by_country(ghsl_pop_dataset_h, location_ghsl_pop, country_mask)
        ghsl_bld_year_h = load_dataset_by_country(ghsl_bld_dataset_h, location_ghsl_bld, country_mask_bld)
        ghsl_pop_year = ghsl_pop_year_l * (year_h - year) / 5 + ghsl_pop_year_h * (year - year_l) / 5
        ghsl_bld_year = ghsl_bld_year_l * (year_h - year) / 5 + ghsl_bld_year_h * (year - year_l) / 5
    else:
        ghsl_pop_year = load_dataset_by_country(ghsl_pop_dataset, location_ghsl_pop, country_mask)
        ghsl_bld_year = load_dataset_by_country(ghsl_bld_dataset, location_ghsl_bld, country_mask_bld)

    # correct for offset in the building layer
    if ghsl_bld_year.shape[1] < ghsl_pop_year.shape[1]:
        ghsl_bld_year_c = np.concatenate([np.zeros([ghsl_pop_year.shape[0], 1]), ghsl_bld_year],axis=1)
    else:
        ghsl_bld_year_c = ghsl_bld_year

    return ghsl_pop_year, ghsl_bld_year_c

def load_hyde_data(year, Year_hyde, Raster_path, location, country_mask):

    year_h = ''
    hyde_dataset_h = ''
    interp = 0

    location_hyde = np.zeros(4)
    location_hyde[0] = np.floor(location[0] / 10) - 1
    location_hyde[1] = np.floor(location[1] / 10) + 10
    location_hyde[2] = np.ceil(location[2] / 10) + 2
    location_hyde[3] = np.ceil(location[3] / 10) + 2
    # correct for offsets
    if location_hyde[2] > 4320:
        location_hyde[0] = 0
        location_hyde[2] = 4320
        col_off = int(np.mod(location[0], 10))
    else:
        col_off = int(np.mod(location[0], 10)) - 1 + 10
    row_off = int(np.mod(location[1], 10)) - 2 + 10
    country_mask_hyde = np.full([int(location_hyde[3]), int(location_hyde[2])], True)

    if year not in Year_hyde:
        # if year is between HYDE dataset, open upper limit dataset for interpolation
        interp = 1
        year_l = max(Year_hyde[Year_hyde < year])
        year_h = min(Year_hyde[Year_hyde > year])
        hyde_dataset_h = rasterio.open(Raster_path + 'HYDE/zip/popc_' + str(year_h) + 'AD.asc')
    else:
        year_l = year
    # open HYDE dataset or its lower limit for interpolation
    hyde_dataset = rasterio.open(Raster_path + 'HYDE/zip/popc_' + str(year_l) + 'AD.asc')
    # open base HYDE dataset (1975, created in ArcGIS)
    hyde_dataset_base = rasterio.open(Raster_path + 'HYDE/popc_1975AD.tif')

    if interp == 1:
        hyde_year_l = load_dataset_by_country(hyde_dataset, location_hyde, country_mask_hyde)
        hyde_year_h = load_dataset_by_country(hyde_dataset_h, location_hyde, country_mask_hyde)
        hyde_year = hyde_year_l * (year_h - year) / 10 + hyde_year_h * (year - year_l) / 10
    else:
        hyde_year = load_dataset_by_country(hyde_dataset, location_hyde, country_mask_hyde)
    hyde_base = load_dataset_by_country(hyde_dataset_base, location_hyde, country_mask_hyde)

    hyde_base_interp = zoom(hyde_base, (10, 10), order = 0, mode = 'grid-constant', grid_mode=True)
    hyde_year_interp = zoom(hyde_year, (10, 10), order = 0, mode = 'grid-constant', grid_mode=True)
    hyde_base_1km = hyde_base_interp[row_off: row_off + int(location[3]), col_off: col_off + int(location[2])]
    hyde_year_1km = hyde_year_interp[row_off: row_off + int(location[3]), col_off: col_off + int(location[2])]
    if location_hyde[2] == 4320:
        hyde_base_1km = np.concatenate([np.zeros([int(location[3]), 1]), hyde_base_1km], axis=1)
        hyde_year_1km = np.concatenate([np.zeros([int(location[3]), 1]), hyde_year_1km], axis=1)
    hyde_base_1km[~country_mask] = 0
    hyde_year_1km[~country_mask] = 0

    return hyde_year_1km, hyde_base_1km

def load_ssp_data(year, Year_ssp, Raster_path, location, country_mask, scenario):

    year_h = ''
    ssp_pop_dataset_h = ''
    ssp_file = Raster_path + 'Wang_SSP/SSP' + str(scenario + 1) + '_'
    interp = 0
    ssp_base_year = Year_ssp[0]

    # offset for the different grid box of Wang's SSP data
    location_ssp_pop = location + [-1, -612, 0, 0]
    if location_ssp_pop[2] > 43200:
        location_ssp_pop[0] = 0
        location_ssp_pop[2] = 43200
        country_mask_ssp = country_mask[:,1:]
    else:
        country_mask_ssp = country_mask

    if year not in Year_ssp:
        # if year is between SSP dataset, open upper limit dataset for interpolation
        interp = 1
        year_l = max(Year_ssp[Year_ssp < year])
        year_h = min(Year_ssp[Year_ssp > year])
        ssp_pop_dataset_h = rasterio.open(ssp_file + str(year_h) + '.tif')
    else:
        year_l = year
    # open SSP dataset or its lower limit for interpolation
    ssp_pop_dataset = rasterio.open(ssp_file + str(year_l) + '.tif')
    # open SSP base year
    ssp_base_dataset = rasterio.open(ssp_file + str(ssp_base_year) + '.tif')

    if interp == 1:
        ssp_pop_year_l = load_dataset_by_country(ssp_pop_dataset, location_ssp_pop, country_mask_ssp)
        ssp_pop_year_h = load_dataset_by_country(ssp_pop_dataset_h, location_ssp_pop, country_mask_ssp)
        ssp_pop_year = ssp_pop_year_l * (year_h - year) / 5 + ssp_pop_year_h * (year - year_l) / 5
    else:
        ssp_pop_year = load_dataset_by_country(ssp_pop_dataset, location_ssp_pop, country_mask_ssp)
    ssp_pop_base = load_dataset_by_country(ssp_base_dataset, location_ssp_pop, country_mask_ssp)

    ssp_pop_base[ssp_pop_base == 255] = 0
    ssp_pop_year[ssp_pop_year == 255] = 0

    if location_ssp_pop[2] == 43200:
        ssp_pop_base = np.concatenate([np.zeros([int(location[3]), 1]), ssp_pop_base], axis=1)
        ssp_pop_year = np.concatenate([np.zeros([int(location[3]), 1]), ssp_pop_year], axis=1)

    return ssp_pop_year, ssp_pop_base

def disaggregate_subnational_GDP(subnational_dataset, location, country_mask, ghsl_pop_year, ghsl_bld_year,
                                 GDP_regio_c, GDP_data_s_c_y, GDPpc_data_s_c_y, FA_data_s_c_y):

    GDP_country_raster = np.zeros([country_mask.shape[0], country_mask.shape[1]])
    FA_country_raster = np.zeros([country_mask.shape[0], country_mask.shape[1]])

    country_regions = load_dataset_by_country(subnational_dataset, location, country_mask)
    Regio_pop = np.zeros([len(GDP_regio_c.index) + 1])
    Regio_bld = np.zeros([len(GDP_regio_c.index) + 1])
    Regio_GDP_pc = np.zeros([len(GDP_regio_c.index) + 1])
    for kr, r in enumerate(GDP_regio_c.index):
        ixr = country_regions == r
        Regio_pop[kr] = ghsl_pop_year[ixr].sum()
        Regio_bld[kr] = ghsl_bld_year[ixr].sum()
    # population and build-up area for cells outside the defined regions
    Regio_pop[-1] = ghsl_pop_year.sum() - Regio_pop[:-1].sum()
    Regio_bld[-1] = ghsl_bld_year.sum() - Regio_bld[:-1].sum()
    # distribute GDP/FA by population and build-up
    Regio_GDP_i = Regio_pop * (GDP_data_s_c_y / Regio_pop.sum()) * np.concatenate([GDP_regio_c.values, np.ones([1])])
    Regio_GDP_ii = Regio_GDP_i * (GDP_data_s_c_y / Regio_GDP_i.sum())
    Regio_GDP_pc[:-1] = ( Regio_GDP_ii[:-1] / Regio_pop[:-1] * 1E9)
    Regio_FA = Regio_GDP_ii * FA_data_s_c_y / GDP_data_s_c_y

    # disaggregate GDP value (60% by population, 40% by buildup area) and fixed assets by buildup area
    for kr, r in enumerate(GDP_regio_c.index):
        ixr = country_regions == r
        GDP_per_pop = Regio_GDP_ii[kr] * 0.6 / Regio_pop[kr] * 1E9
        GDP_per_bld = Regio_GDP_ii[kr] * 0.4 / Regio_bld[kr] * 1E9
        GDP_country_raster[ixr] += ghsl_pop_year[ixr] * GDP_per_pop + ghsl_bld_year[ixr] * GDP_per_bld
        # disaggregate fixed assets by buildup area
        FA_per_bld = Regio_FA[kr] / Regio_bld[kr] * 1E9
        FA_country_raster[ixr] += ghsl_bld_year[ixr] * FA_per_bld

    if (Regio_pop[-1] > 0) & (Regio_bld[-1] > 0):
        # disaggregate GDP and fixed assets for areas outside defined regions
        ixr = np.isin(country_regions, GDP_regio_c.index, invert=True)
        GDP_per_pop = Regio_GDP_ii[-1] * 0.6 / Regio_pop[-1] * 1E9
        GDP_per_bld = Regio_GDP_ii[-1] * 0.4 / Regio_bld[-1] * 1E9
        GDP_country_raster[ixr] += ghsl_pop_year[ixr] * GDP_per_pop + ghsl_bld_year[ixr] * GDP_per_bld
        # disaggregate fixed assets by buildup area
        FA_per_bld = Regio_FA[-1] / Regio_bld[-1] * 1E9
        FA_country_raster[ixr] += ghsl_bld_year[ixr] * FA_per_bld

    return GDP_country_raster, FA_country_raster