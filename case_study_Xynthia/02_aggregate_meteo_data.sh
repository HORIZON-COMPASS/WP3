#!/bin/bash
#SBATCH --qos=priority
#SBATCH --partition=priority
#SBATCH --job-name=aggregate_ERA_data
#SBATCH --account=isimip
#SBATCH --output=aggr-%j.out
#SBATCH --error=aggr-%j.err
#SBATCH --cpus-per-task=16

## compute wind speed from raw wind vectors in ERA5-Land
for y in {1950..2023}
do
	year="$y"
	i1="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/ERA5Land_sfcWind_${year}_1.grib"
	i2="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/ERA5Land_sfcWind_${year}_2.grib"
	i3="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/ERA5Land_sfcWind_${year}_3.grib"
	i4="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/ERA5Land_sfcWind_${year}_4.grib"
	i5="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/ERA5Land_sfcWind_${year}_5.grib"
	i6="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/ERA5Land_sfcWind_${year}_6.grib"
	i7="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/ERA5Land_sfcWind_${year}_7.grib"
	i8="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/ERA5Land_sfcWind_${year}_8.grib"
	i9="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/ERA5Land_sfcWind_${year}_9.grib"
	i10="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/ERA5Land_sfcWind_${year}_10.grib"
	i11="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/ERA5Land_sfcWind_${year}_11.grib"
	i12="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/ERA5Land_sfcWind_${year}_12.grib"
	o_sfcWind="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/sfcWind_ERA5_${year}.nc"
	cdo -f nc4c -z zip expr,sfcWind="sqrt(var165*var165+var166*var166)" -sellonlatbox,-6,10,41,52 -selname,var165,var166 -mergetime $i1 $i2 $i3 $i4 $i5 $i6 $i7 $i8 $i9 $i10 $i11 $i12 $o_sfcWind
done

## compute wind speed from raw wind vectors in ERA5
for y in {1950..2023}
do
	year="$y"
	i1="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/ERA5_sfcWind_${year}_1.grib"
	i2="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/ERA5_sfcWind_${year}_2.grib"
	i3="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/ERA5_sfcWind_${year}_3.grib"
	i4="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/ERA5_sfcWind_${year}_4.grib"
	i5="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/ERA5_sfcWind_${year}_5.grib"
	i6="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/ERA5_sfcWind_${year}_6.grib"
	i7="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/ERA5_sfcWind_${year}_7.grib"
	i8="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/ERA5_sfcWind_${year}_8.grib"
	i9="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/ERA5_sfcWind_${year}_9.grib"
	i10="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/ERA5_sfcWind_${year}_10.grib"
	i11="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/ERA5_sfcWind_${year}_11.grib"
	i12="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/ERA5_sfcWind_${year}_12.grib"
	o_sfcWind="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/sfcWind_ERA5_${year}.nc"
	cdo -f nc4c -z zip expr,sfcWind="sqrt(var165*var165+var166*var166)" -sellonlatbox,-6,10,41,52 -selname,var165,var166 -mergetime $i1 $i2 $i3 $i4 $i5 $i6 $i7 $i8 $i9 $i10 $i11 $i12 $o_sfcWind
done

## Combine ERA5-Land and ERA5 files
# grid file
era5land_name="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/sfcWind_ERA5_2021.nc"
grid_file="era5_land_grid.txt"
cdo griddes $era5land_name > $grid_file

# weight file
era5_name="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/sfcWind_ERA5_2021.nc"
weight_file="sfcWind_weights_ERA5.nc"
cdo gennn,$grid_file $era5_name $weight_file

# mask file
era5land_mask="ERA5Land_mask.nc"
cdo -f nc4c -z zip setmisstoc,0 -expr,sfcWind="(sfcWind >= 0) ? 1 : 0" -seltimestep,1 $era5land_name $era5land_mask

for y in {1950..2023}
do
	year="$y"
	era5_file="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/sfcWind_ERA5_${year}.nc"
	era5_file_regrid="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5/sfcWind_regrid_ERA5_${year}.nc"
	era5land_file="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_ERA5Land/sfcWind_ERA5_${year}.nc"
	oname="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_combined/sfcWind_ERA5_${year}.nc"
	cdo -f nc4c -z zip remap,$grid_file,$weight_file $era5_file $era5_file_regrid
	cdo -f nc4c -z zip ifthenelse $era5land_mask $era5land_file $era5_file_regrid $oname
done

## Split data into smaller grids
for year in {1950..2023}
do
	era5_comb="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_combined/sfcWind_ERA5_${year}.nc"
	cdo -f nc4c -z zip distgrid,10,10 $era5_comb /p/tmp/dominikp/COMPASS/Meteo_data/Wind_combined/sfcWind_ERA5_${year}_
done

## Merge timeseries to have all timesteps in single files
for g in {0..9}
do
	era5_ga="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_combined/sfcWind_ERA5_$g.nc"
	cdo -f nc4c -z zip -mergetime sfcWind_ERA5_????_0000$g.nc $era5_ga
	rm sfcWind_ERA5_????_0000$g.nc
done

for g in {10..99}
do
	era5_ga="/p/tmp/dominikp/COMPASS/Meteo_data/Wind_combined/sfcWind_ERA5_$g.nc"
	cdo -f nc4c -z zip -mergetime sfcWind_ERA5_????_000$g.nc $era5_ga
	rm sfcWind_ERA5_????_000$g.nc
done
