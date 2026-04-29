import pytest
import re

import xarray as xr

from common import runcmd, make_nc
from splitnc import determine_field_vars


@pytest.mark.parametrize(
    "cdl_file,cmd_options,field_regex,num_nc_files",
    [
        (
            # Test a monthly atmosphere file
            "aiihca.pa-234501_mon.cdl",
            "--shared-vars latitude_longitude --rename-regex '(?P<newname>.+)_\\d+'",
            "fld_.+",
            217,
        ),
        (
            # Test a daily atmosphere file
            "aiihca.pe-234501_dai.cdl",
            "--shared-vars latitude_longitude --rename-regex '(?P<newname>.+)_\\d+'",
            "fld_.+",
            36,
        ),
        (
            # Test a monthly ice file
            "iceh-1monthly-mean_2345-01.cdl",
            "--shared-vars uarea,tmask,tarea,VGRDb,VGRDi,VGRDs",
            "(ai|dv|si).+",
            53,
        ),
        (
            # Test a daily ice file
            "iceh-1daily-mean_2345-01.cdl",
            "--shared-vars uarea,tmask,tarea,VGRDb,VGRDi,VGRDs",
            "(ai|dv|si).+",
            25,
        ),
        (
            # Test a monthly atmosphere file with a regex for shared-vars
            # Previously when shared-var regex were resolved after field-var, this failed
            "aiihca.pa-234501_mon.cdl",
            "--shared-vars latitude_lon.+ --rename-regex '(?P<newname>.+)_\\d+'",
            "fld_.+",
            217,
        ),
    ],
)
def test_splitnc(tmp_path, cdl_file, cmd_options, field_regex, num_nc_files):
    """
    Test running splitnc from the command line
    """
    # Create a file to test on
    ncfile = make_nc(tmp_path, f"test/data/{cdl_file}")

    # Attempt to split the file
    output_dir = tmp_path / "single_field"
    cmd = f"python splitnc.py {cmd_options} --output-dir {output_dir} {ncfile}"
    runcmd(cmd)

    # Check all the output files have one and only one variable matching the field_regex
    output_files = list(output_dir.glob("*.nc"))
    for output_file in output_files:
        print(output_file)
        ds = xr.open_dataset(
            output_file, decode_times=xr.coders.CFDatetimeCoder(use_cftime=True)
        )

        # Only one variable in each single-field file should match the field_regex
        count = 0
        for v in ds.variables:
            if re.match(field_regex, v):
                count += 1

        assert count == 1

    assert len(output_files) == num_nc_files


@pytest.mark.parametrize(
    "cdl_file,field_regex",
    [
        (
            # Test a simple cdl
            "simple.cdl",
            "field",
        ),
        (
            # Test a simple cdl that has co-dependent fields - i.e. none will be detected
            "simple_circular.cdl",
            "none",
        ),
        (
            # Test a monthly atmosphere file - will also pick up latitude_longitude
            "aiihca.pa-234501_mon.cdl",
            "fld_.+|latitude_longitude",
        ),
        (
            # Test a daily atmosphere file - will also pick up latitude_longitude
            "aiihca.pe-234501_dai.cdl",
            "fld_.+|latitude_longitude",
        ),
        (
            # Test a monthly ice file - will also pick up some extra fields
            "iceh-1monthly-mean_2345-01.cdl",
            "(ai|dv|si||tarea|tmask|uarea|VGRD).*",
        ),
        (
            # Test a daily ice file - will also pick up some extra fields
            "iceh-1daily-mean_2345-01.cdl",
            "(ai|dv|si||tarea|tmask|uarea|VGRD).*",
        ),
    ],
)
def test_determine_field_vars(tmp_path, cdl_file, field_regex):
    """
    Test the functionality for the automatic determinations of field vars
    """
    # Create a file to test on
    ncfile = make_nc(tmp_path, f"test/data/{cdl_file}")

    decoder = xr.coders.CFDatetimeCoder(use_cftime=True)
    with xr.open_dataset(ncfile, decode_times=decoder) as ds:
        field_list = determine_field_vars(ds)

        # Check all the discovered fields match the regex
        print(field_list)
        assert all([re.match(field_regex, v) for v in field_list])
