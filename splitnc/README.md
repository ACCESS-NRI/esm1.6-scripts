# splitnc
This script splits multi-field netCDF files into single-field files.
It is designed to work on ESM1.6's atmosphere and ice files.

### Automatic Field Identification
By default `splitnc` will attempt to identify the fields for a multi-field netCDF files by looking for variables that no other variables depend on.
A variable that no others depend on is likely to be a field.
E.g. many variables depend on `time`, but none depend on `sea_surface_temperature`.

Alternatively the fields to separate to individual files can be specified as a comma sepated list with the `--field-vars` command line option.

### "Ancillary" Variables

Some variables with no dependents should not be separated into individual files, these variables must be manually identified with the `--shared-vars` command line option.
These variables will then be present in every output file.

If there are ancillary fields that should only be present in only some of the output field files then multiple invocations of `splitnc` using `--field-vars` and `--shared-vars` will be required.

Example of these variables are the `latitude_longitude` found in atmosphere files or the `uarea`, `tmask`, `tarea`, `VGRDb`, `VGRDi`, `VGRDs` variables from ice files.

### Config File

TODO: Add a commandline options to ingest a file to supply the rest of the command line options.

### Command Line Options

```quote
usage: splitnc [-h] [--field-vars FIELD_VAR1,FIELD_VAR2,...] [--shared-vars SHARED_VAR1,SHARED_VAR2,...]
               [--output-name-pattern OUTPUT_NAME_PATTERN] [--rename-regex REGEX] [--output-dir OUTPUT_DIR] [--overwrite] [-v]
               filepaths [filepaths ...]

Splits a multi-field netCDF file into separate one-field files

positional arguments:
  filepaths             One or more filepaths to process

options:
  -h, --help            show this help message and exit
  --field-vars FIELD_VAR1,FIELD_VAR2,...
                        Specify the names of the field variables to split into separate files - dimensions, bounds, and
                        coordinates of these fields will be included in each file. Disables automatic field variable
                        identification. Regex patterns can be used here.
  --shared-vars SHARED_VAR1,SHARED_VAR2,...
                        Specify the names of variables that should be shared across files that cannot be automatically identified,
                        as a comma separated list. Regex patterns can be used here.
  --output-name-pattern OUTPUT_NAME_PATTERN
                        The pattern to use for the names of output files. Use "{field_var}" for the name of the field variables,
                        and "{filename}" for the original filename. Defaults to "{field_var}_{filename}".
  --rename-regex REGEX  Look for duplicated coordinate names that match the given regex and rename them to the first "newname"
                        capture group in the regex. E.g. "(?P<newname>.*)_\d+" will match "time_0" and rename it to "time".
  --output-dir OUTPUT_DIR
                        Output directory for the processed files. If not given output files will be placed in the same directory
                        as the original file.
  --overwrite           Overwrite existing files
  -v, --verbose
```

### Example Usage

`splitnc` just needs `xarray` and `netCDF4`.
On Gadi use load any module with `xarray`, such as `conda/analysis3`.
Alternatively create a new python environment and install `xarray` and `netCDF4`.

#### Atmosphere
To use this script for split multi-field atmosphere files from ACCESS-ESM1.6:
```bash
python split-nc.py --shared-vars latitude_longitude  --rename-regex "(?P<newname>.*)_\\d+" $INPUT_DIR/*.nc
```

`splitnc` will automatically determine which variables are fields by looking at which variables depend on other variables. Variables with nothing depending on them are deemed to be fields.
Alternatively one can use `--field-vars fld_.*` to match the variable names in these files.

The `--rename-regex` option with the supplied regex will rename variables like
`time_0` or `pseudo_level_0` are renamed to `time` or `pseudo_level`.

The `--shared-vars` option will ensure that the variable `latitude_longitude` is
included in all files even though none of the field variable depend on it.

#### Ice
To use this script for split multi-field ice files from ACCESS-ESM1.6:
```bash
python split-nc.py --shared-vars uarea,tmask,tarea,VGRDb,VGRDi,VGRDs $INPUT_DIR/*.nc
```

With ice files the shared-vars are different and there are no duplicated variables that require renaming.
