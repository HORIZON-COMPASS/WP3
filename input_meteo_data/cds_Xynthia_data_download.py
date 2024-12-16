import cdsapi
import os

c = cdsapi.Client()

years = range(2021,2024)
months = range(1,13)

for y in years:
    for m in months:

        ## ERA5-Land
        if os.path.isfile('/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/ERA5Land_sfcWind_'+str(y)+'_'+str(m)+'.grib'):
            print('Already downloaded')
        else:
            c.retrieve(
                'reanalysis-era5-land',
                {
                    'variable': [
                        '10m_u_component_of_wind', '10m_v_component_of_wind'
                    ],
                    'year': str(y),
                    'month': str(m),
                    'day': [
                        '01', '02', '03', '04', '05', '06', '07', '08', '09',
                        '10', '11', '12', '13', '14', '15', '16', '17', '18',
                        '19', '20', '21', '22', '23', '24', '25', '26', '27',
                        '28', '29', '30', '31',
                    ],
                    'time': [
                        '00:00', '01:00', '02:00', '03:00', '04:00', '05:00',
                        '06:00', '07:00', '08:00', '09:00', '10:00', '11:00',
                        '12:00', '13:00', '14:00', '15:00', '16:00', '17:00',
                        '18:00', '19:00', '20:00', '21:00', '22:00', '23:00',
                    ],
                    'area': [
                        52, -6, 41, 10, ## France
                    ],
                    'data_format': 'grib',
                    'download_format': 'unarchived',
                },
                '/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/ERA5Land_sfcWind_'+str(y)+'_'+str(m)+'.grib')

        ## additional ERA5 data for gap-filling in coastal areas
        if os.path.isfile('/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/ERA5_sfcWind_'+str(y)+'_'+str(m)+'.grib'):
            print('Already downloaded')
        else:
            c.retrieve(
                'reanalysis-era5-single-levels',
                {
                    'product_type': 'reanalysis',
                    'variable': [
                        '10m_u_component_of_wind', '10m_v_component_of_wind',
                    ],
                    'year': str(y),
                    'month': str(m),
                    'day': [
                        '01', '02', '03', '04', '05', '06', '07', '08', '09',
                        '10', '11', '12', '13', '14', '15', '16', '17', '18',
                        '19', '20', '21', '22', '23', '24', '25', '26', '27',
                        '28', '29', '30', '31',
                    ],
                    'time': [
                        '00:00', '01:00', '02:00', '03:00', '04:00', '05:00',
                        '06:00', '07:00', '08:00', '09:00', '10:00', '11:00',
                        '12:00', '13:00', '14:00', '15:00', '16:00', '17:00',
                        '18:00', '19:00', '20:00', '21:00', '22:00', '23:00',
                    ],
                    'area': [
                        52, -6, 41, 10, ## France
                    ],
                    'data_format': 'grib',
                    'download_format': 'unarchived',
                },
                '/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/ERA5_sfcWind_'+str(y)+'_'+str(m)+'.grib')