# Produce atmosphere restart for ESM1.6

Creates a new restart file with a new vegetation distribution, based on a previous UM restart. The default STASHmaster files used require ```access``` and ```rp23``` group memberships on Gadi, with the ```xp65``` analysis environment for ```mule```.

The process is comprised of 3 scripts:

1. [convert_UM_restart_to_netcdf.py](#convert_UM_restart_to_netcdf.py): converts all the CABLE fields (which is defined as all fields which have a pseudo-level dimension of 17) to NetCDF, replacing all instances of ```/``` with ``` PER ```, as the ```/``` is not allowed in NetCDF names.
2. [adjust_restart_for_new_land_cover.py](#adjust_restart_for_new_land_cover.py): performs the remapping of restart fields for the new vegetation map. Detailed description of the script below.
3. [add_netcdf_fields_to_UM_restart.py](#add_netcdf_fields_to_UM_restart.py): take the generated NetCDF file from ```remap_vegetation.py``` and copy the variables into their respective restart fields.

These are executed via ```run_adjust_restart.sh```. This script has placeholders for the required input/output names required for the process.

## convert_UM_restart_to_netcdf.py

### CLI args

* ```-i/--input```: Reference UM7 restart file to convert to NetCDF.
* ```-o/--output```: Name to write the NetCDF file to.
* ```-s/--stash```: STASHmaster files to use when generating NetCDF names. Defaults to ```/g/data/access/umdir/vn7.3/ctldata/STASHmaster/STASHmaster_A,/g/data/rp23/experiments/2024-03-12_CABLE4-dev/lw5085/CABLE-as-ACCESS/prefix.PRESM_A```, which is accurate for ESM1.5/ESM1.6 as of 17/07/2025.

### Description

Takes a subset of the fields from the UM restart and converts them to NetCDF. The specific fields taken are those which are considered to be "land" variables, which at the moment is defined to be any variables with 1 or 17 pseudo-levels (surface and per-tile variables respectively). NetCDF does not allow the use of ```"/"``` characters, which is often used in UM7 field names, so these have been replaced with ```" PER "``` in the NetCDF file.

## adjust_restart_for_new_land_cover_map.py

### CLI args

* ```-i/--input```: NetCDF representation of UM restart to map onto a new vegetation distribution.
* ```-o/--output```: Name to write the generated NetCDF file to.
* ```-m/--vegetation_map```: NetCDF containing the new vegetation distribution. The vegetation distribution is expected to be in the ```"fraction"``` variable, and have dimensions of ```(time, veg, lat, lon)```.
* ```--fill-all```: If specified, all the land tiles are filled with physically meaningful values, as opposed to only the active tiles.
* ```-c/--config```: Configuration file describing the remapping process.

### Description

The ACCESS-ESM1.5 restart only contains physically valid values on active tiles i.e. tiles that have non-zero fraction in the grid cell at some point during the LUC dataset. Thus changing the vegetation map requires major changes to all tiled values in the restart. There are two "types" of tiled variables which should be treated differently.

The vegetation agnostic variables, like soil moisture and temperature. These variables are not required to be kept distinct across tiles. In this case, all tiles are given the fraction weighted cell average e.g. in the original restart, a cell has tile 1 with area fraction 0.75 and soil temperature of 300K, tile 2 with area fraction of 0.25 and soil temperature of 305K, the new soil temperature of all tiles on the cell would be 300*0.75 + 305 * 0.25. 

The vegetation specific variables, primarily the nutrient pools. These variables should remain distinct across tiles. The fill process is as follows:

1. Identified valid vegetation type mappings from the old vegetation types to the new. For most vegetation types, this is a 1-to-1 relationship i.e. only vegetation type 1 is valid for filling vegetation type 2, type 2 is valid for type 2 etc. For instances of new vegetation types being added, it is possible to map existing types to the new type, so that new types get an average of the types that were mapped to it. For example, in ESM1.6, C4 grasses (type 10) were added as a vegetation type, which was not included in ACCESS-ESM1.5. Vegetation types 6, 7 and 9 were considered valid vegetation types to fill the C4 grasses. This is demonstrated in the provided example configuration.

Following steps are applied at every tile on all land grid cell:

2. Check if the old vegetation surface fractions contained non-zero fraction of a vegetation type valid for the current tile. If yes, then the new value is set to the old value on that tile (non-weighted average if multiple valid vegetation types have non-zero fraction, as with C4 grasses). If not, continue to stage 3.

3. Check for valid vegetated tiles in a small area around the original cell, where the area is defined by a number of latitude and longitude indices either side of the original cell. If any valid tiles exist, then take the non-weighted average of all valid tiles. If no valid tiles exist, continue to step 4. In the example configuration, 2 cells either side are used (i.e. a 5x5 square of cells around the original cell).

4. Check for valid vegetation tiles in a latitude band around the original cell. If any valid tiles exist, then take the non-weighted average of all valid tiles. If no tiles exist, then continue to step 5. The latitude band in the example configuration is 8 cells either side (+- 10 degrees).

5. Check for valid vegetation tiles globally. If any valid tiles exist, then take the non-weighted average of all valid tiles. If no tiles exist, then set the value to 0.0.

### Configuration file

The configuration file contains is a YAML file which contains:

* ```vegetation_map```: A dictionary of lists which designates which PFTs can be used as sources for new PFTs. In the above example, where PFTs 6, 7 and 9 were valid sources for PFT 10 on the new distribution, then it would read ```vegetation_map: 10: [6, 7, 9]```. Note this uses 1-based indexing. All PFTs not specified only have the equivalent PFT as a source i.e. PFT 1 on the old distribution is the only source for PFT 1 on the new distribution, PFT 2 for PFT 2 and so on. The provided configuration file demonstrates this example.
* ```search_radius```: Cell "radius" to search in during the second search stage. For example, if ```search_radius: 2```, then it will search within a 5x5 box around the given point for valid tiles. Defaults to 2.
* ```latitude_band```: Cell band to search in during the third search stage. For example, if ```latitude_band: 8```, then it will search within a latitude band of 19 cells for valid tiles. Defaults to 8.
* ```minimum_tiles```: Minimum number of valid tiles found in a search to be considered "successful". For example, if ```minimum_tiles: 3```, and the second search (nearby box) only found 2 valid tiles, that search would be considered unsuccessful and the process would move onto the third search stage (latitude band). Defaults to 1.
* ```per_cell```: List of fields that should be considered "per cell" variables i.e. vegetation agnostic as described above. Does not have a default- it is recommended to take this from the provided config.
* ```per_tile```: List of fields that should be considered "per tile" variables i.e. vegetation specific. Does not have a default- it is recommended to take this from the provided config.

## add_netcdf_fields_to_UM_restart.py

### CLI args

* ```-i/--input```: NetCDF file to merge into a reference UM restart.
* ```-o/--output```: Name to write the resulting UM restart to.
* ```-r/--restart```: Reference restart to place NetCDF fields into.
* ```-s/--stash```: STASHmaster files to use with the UM restart files, for determining where to place NetCDF fields. Defaults to ```/g/data/access/umdir/vn7.3/ctldata/STASHmaster/STASHmaster_A,/g/data/rp23/experiments/2024-03-12_CABLE4-dev/lw5085/CABLE-as-ACCESS/prefix.PRESM_A```, which is accurate for ESM1.5/ESM1.6 as of 17/07/2025.

### Description

Takes the prescribed NetCDF file and reference UM restart files, and attempts to place the NetCDF variables into the relevant UM fields. Given the restriction on using ```"/"``` in NetCDF names, and the propensity for its use in UM files, all instances of ```" PER "``` in NetCDF names are replaced with ```"/"``` when searching for the relevant UM field.
