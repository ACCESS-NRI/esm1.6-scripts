"""
This script will check the values of two datasets against each other.

It is intended to be used to confirm the integrity of data produced by `splitnc`.
"""
import argparse
import logging
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import xarray as xr

# Get logging instance
logger = logging.getLogger(__name__)

## FUNCTIONS
def process_file(all_source_files, dest_file, realm):
    logger.debug(f"Processing {dest_file} for {realm}")

    decoder = xr.coders.CFDatetimeCoder(time_unit='s', use_cftime=True)
    with xr.open_dataset(dest_file, decode_times=decoder) as ds_dest:
        varname = ds_dest.attrs['variable_id']

        if varname == 'scalar':
            # Skip this file
            return

        # Get the sources files for this dest file
        if realm == "atmosphere":
            source_files = get_sources_atmo(all_source_files, ds_dest)
        elif realm == "ice":
            source_files = get_sources_ice(all_source_files, ds_dest)
        elif realm == "ocean":
            source_files = get_sources_ocean(all_source_files, ds_dest)
        else:
            raise argparse.ArgumentError(f"Invalid argument given for realm: {realm}")

        logger.debug(f"Matching files for {dest_file.name}: {source_files}")

        # Drop any variable from the source that aren't in dest
        # This should speed up loading the ds since open_mfdataset has less to check
        # - Also need to look for the cases where variable_id != to the name of the variable
        #     e.g. some foo_max/foo_min
        # - Also need to drop any duplicate coordinates e.g. height if we need height_0
        def preprocess(ds):
            try:
                da = ds[varname]
            except KeyError as e:
                for suffix in ['_max', '_min']:
                    v = varname + suffix
                    if varname + suffix in ds:
                        da = ds[v]
                        break
                else:
                    raise e

            if 'time_0' in da.dims:
                ds = ds.drop_vars('time')
                ds = ds.rename({"time_0": "time"})

            drop_vars = [v for v in list(ds.variables) if v not in list(ds_dest.variables)]
            return ds.drop_vars(drop_vars)

        # Set some of these args to default values to silence warnings
        with xr.open_mfdataset(source_files, decode_times=decoder, data_vars='all',
                               coords='different', compat='no_conflicts',
                               preprocess=preprocess) as ds_source:
            logger.debug(f"Verifying data for {varname}")
            verify_data(ds_source, ds_dest, varname)

            logger.info(f"Successfully verified {dest_file.name}")


def verify_data(ds_source, ds_dest, varname):
    try:
        da_source = ds_source[varname]
        da_dest = ds_dest[varname]
    except KeyError as e:
        for suffix in ['_max', '_min']:
            v = varname + suffix
            if varname + suffix in ds_dest:
                da_source = ds_source[v]
                da_dest = ds_dest[v]
                break
        else:
            raise e

    assert np.array_equal(da_source.to_numpy(), da_dest.to_numpy(), equal_nan=True), \
        f"Failed to verify {ds_dest.encoding['source']}"


## Atmosphere
@lru_cache
def _get_atmos_freqs(source_files: tuple):
    # Need to use a tuple instead of a list so func can be cached
    atmos_regex = r"aiihca\.p(?P<freq>[aceij])-\d{4}\d{2}(?:_mon|_dai|_3hr|_6hr)?\.nc"

    # Need to map freq character to freq vocab
    atmos_freq_mapping = {
        "a": "1mon",
        "c": "1hr",
        "e": "1day",
        "i": "3hr",
        "j": "6hr",
    }

    freq_list = []
    for f in source_files:
        m = re.search(atmos_regex, f.name)

        assert m, f"Failed to match atmos regex with file {f.name}"

        freq_list.append(atmos_freq_mapping[m['freq']])

    return freq_list


def get_sources_atmo(source_files, ds_dest):
    source_freqs = _get_atmos_freqs(tuple(source_files))

    # Atmos files should be 12 to 1
    freq = ds_dest.attrs['frequency']

    matching_files = [f for f, s_freq in zip(source_files, source_freqs) if freq==s_freq]

    match_len = len(matching_files)
    assert match_len == 12, \
            f"There should 12 matching source files for {ds_dest.encoding['source']}" \
            f"Not {match_len}:{'\n'.join([f.name for f in matching_files])}"

    return matching_files


## Ice
def _get_ice_freqs(source_files: tuple):
    # Need to use a tuple instead of a list so func can be cached
    ice_regex = r"iceh-(?P<freq>1(daily|monthly))-mean_\d{4}-\d{2}\.nc"

    # Need to map freq character to freq vocab
    ice_freq_mapping = {
        "1monthly": "1mon",
        "1daily": "1day",
    }

    freq_list = []
    for f in source_files:
        m = re.search(ice_regex, f.name)

        assert m, f"Failed to match ice regex with file {f.name}"

        freq_list.append(ice_freq_mapping[m['freq']])

    return freq_list


def get_sources_ice(source_files, ds_dest):
    source_freqs = _get_ice_freqs(tuple(source_files))
    
    # ice files should be 12 to 1
    freq = ds_dest.attrs['frequency']

    matching_files = [f for f, s_freq in zip(source_files, source_freqs) if freq==s_freq]

    match_len = len(matching_files)
    assert match_len == 12, \
            f"There should 12 matching source files for {ds_dest.encoding['source']}" \
            f"Not {match_len}:{'\n'.join([f.name for f in matching_files])}"

    return matching_files


## Ocean
@lru_cache
def _get_ocean_vars_freq(source_files: tuple):
    # Need to use a tuple instead of a list so func can be cached
    ocean_regex = r"(?:oceanbgc|ocean)(?:-\dd)?-(?P<var>[^-]+)-(?P<freq>[^-.]+).*\.nc"

    var_freq_list = []
    for f in source_files:
        m = re.search(ocean_regex, f.name)
        assert m, f"Failed to match ocean regex with file {f.name}"

        var_freq_list.append((m['var'], m['freq']))

    return var_freq_list


def get_sources_ocean(source_files, ds_dest):
    source_vars_freqs = _get_ocean_vars_freq(tuple(source_files))

    # Ocean files have a 1-to-1 relationship
    varname = ds_dest.attrs["variable_id"]
    freq = ds_dest.attrs["frequency"]

    matching_files = [f for f, (v, fr) in zip(source_files, source_vars_freqs) if varname==v and freq==fr]

    match_len = len(matching_files)
    assert match_len == 1, \
        f"There should only be one matching source file for {ds_dest.encoding['source']} " \
        f"Not {match_len}:\n{'\n'.join([f.name for f in matching_files])}"
    
    return matching_files


## MAIN
def parse_args():
    parser = argparse.ArgumentParser(
        "check_esm1p6_data.py"
    )

    parser.add_argument(
        "-s", "--source",
        nargs="*",
        help="The list of filepaths that contain the source data"
    )
    parser.add_argument(
        "-d", "--destination",
        nargs="*",
        help="The filepath that contains the destination data"
    )
    parser.add_argument(
        "-r", "--realm",
        choices=["atmosphere", "ice", "ocean"],
        help="Which realm the files belong to"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Use debug level logging"
    )

    return parser.parse_args()

def setup_logging(verbose=False):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M",
    )

def main():
    args = parse_args()

    setup_logging(args.verbose)

    logger.debug(f"Command line arguments: {args}")

    # Turn all filepaths to Path objects and check they exist
    source_files = [Path(s) for s in args.source]
    dest_files = [Path(d) for d in args.destination]

    for s in source_files:
        if not s.exists():
            raise FileNotFoundError(f"Source file appears to be missing: {s}")

    for d in dest_files:
        if not d.exists():
            raise FileNotFoundError(f"Destination file appears to be missing: {d}")

    for dest_file in dest_files:
        process_file(
            all_source_files=source_files,
            dest_file=dest_file,
            realm=args.realm
        )


if __name__ == "__main__":
    main()
