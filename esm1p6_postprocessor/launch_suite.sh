#!/bin/bash

# This script generate config and launches cylc suites for a given list of datasets

DATASET_LIST=(
    "dataset1"
    "/scratch/tm70/jt4085/esm16_examples/*"
)

module load cylc

for dataset_glob in "${DATASET_LIST[@]}"; do
    # Iterate again incase a glob was given
    # This will fail if there are spaces in the paths
    for dataset_path in $dataset_glob; do
        # Use the last directory as the run name
        run_name=`basename $dataset`

        # Check the path exists

        # Start a cylc suite for this dataset
        # Need to set the dataset's path and the run's name
        cylc install \
            -D "[template variables]DATASET_DIR=\"$dataset_path\""
            --run-name $run_name \
            .

        cylc play data_postprocessing_suite/$run_name --pause
    done
done
