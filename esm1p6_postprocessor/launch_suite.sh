#!/bin/bash

# This script launches cylc suites for a given list of datasets
# Suites are installed and started paused
# To interact with all the suites at once use cylc commands with 
# wildcards, e.g.:
#  cylc release --all esm1p6_postprocessor/*

# An array of string paths to datasets, globs are permitted
# Do not use any paths with spaces
DATASET_LIST=(
    "/g/data/p73/archive/CMIP7/ACCESS-ESM1-6/production/*"
)

#### SCRIPT
set -e

module load cylc

for dataset_glob in "${DATASET_LIST[@]}"; do
    # Iterate again incase a glob was given
    # This will fail if there are spaces in the paths
    for dataset_path in $dataset_glob; do
        # Use the last directory as the run name
        run_name=`basename $dataset_path`

        # Check the path exists and is a directory
        if [ ! -d $dataset_path ]; then
            echo "$run_name doesn't exist or isn't a directory - skipping"
            continue
        fi

        # Check that output000 is a subdirectory
        # This supports simple path globs with non-dataset dirs
        if [ ! -d $dataset_path/output000 ]; then
            echo "No output000 found for $run_name - skipping"
            continue
        fi

        # Start a cylc suite for this dataset
        # Need to set the dataset's path and the run's name
        cylc install \
            -D "[template variables]DATASET_DIR=\"$dataset_path\"" \
            --run-name $run_name \
            .

        cylc play esm1p6_postprocessor/$run_name --pause
    done
done
