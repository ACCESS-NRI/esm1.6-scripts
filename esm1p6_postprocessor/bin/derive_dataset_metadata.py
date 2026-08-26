"""
Extracts additional metadata for a given dataests from "cmip7_fastrack_parents" spreadsheet
https://anu365.sharepoint.com/:x:/r/sites/CMIP7Workshop/Shared%20Documents/Submissions/ACCESS-ESM1.6/cmip7_fastrack_parents.xlsx?d=wc95a9a961ed646fc9aca823527f2ebc8&csf=1&web=1&e=m4Pzbf

Extra data is dumped into a yaml file for consumption by addmeta

Sheet has been copy-pasted into conf/dataset_metadata.csv
"""
import argparse

import pandas as pd
import yaml


def get_metadata(dataset_name, csv_path):
    cols_to_use = [
        'experiment_uuid',
        'parent_experiment',
        'parent_experiment_id',
        'branch_time_in_parent',
        'experiment_repo',
        'run_id',
        'base_configuration',
    ]

    df = pd.read_csv(csv_path, delimiter='\t')
    row = df[df['experiment_name']==dataset_name]

    assert len(row) == 1, f"Number of rows that match {dataset_name} is not 1"

    return row[cols_to_use].to_dict(orient='records')[0]


def write_metadata(d, output_file):
    with open(output_file, 'w') as f:
        yaml.dump({"global": d}, f)


## MAIN
def parse_args():
    parser = argparse.ArgumentParser(
        "check_esm1p6_data.py"
    )

    parser.add_argument(
        "-d", "--dataset-name",
        action='store',
        required=True,
        help="The name of the dataset to extract the metadata conf for"
    )
    parser.add_argument(
        "-c", "--conf-csv",
        action='store',
        required=True,
        help="The path to the config csv that contains the metadata for experiments"
    )
    parser.add_argument(
        "-o", "--output-yaml",
        action='store',
        required=True,
        help="The path to the output yaml"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    metadata = get_metadata(args.dataset_name, args.conf_csv)

    for k, v in metadata.items():
        assert not pd.isna(v), f"Missing metadata {k} for {args.dataset_name}"

    write_metadata(metadata, args.output_yaml)


if __name__ == "__main__":
    main()
