import pytest
import re

import xarray as xr

from common import runcmd, make_nc

@pytest.mark.parametrize(
    "cdl_file,cmd_options,field_regex",
    [
        (
            # Test a monthly atmosphere file
            "aiihca.pa-234501_mon.cdl",
            "--shared-vars latitude_longitude --rename-regex '(?P<newname>.*)_\\d+'",
            "fld_.+",
        ),
        (
            # Test a daily atmosphere file
            "aiihca.pe-234501_dai.cdl",
            "--shared-vars latitude_longitude --rename-regex '(?P<newname>.*)_\\d+'",
            "fld_.+",
        ),
        (
            # Test a monthly ice file
            "iceh-1monthly-mean_2345-01.cdl",
            "--shared-vars uarea,tmask,tarea,VGRDb,VGRDi,VGRDs",
            "(ai|dv|si).+",
        ),
        (
            # Test a daily ice file
            "iceh-1daily-mean_2345-01.cdl",
            "--shared-vars uarea,tmask,tarea,VGRDb,VGRDi,VGRDs",
            "(ai|dv|si).+",
        ),
    ]
)
def test_splitting(tmp_path, cdl_file, cmd_options, field_regex):
    # Create a file to test on
    ncfile = make_nc(tmp_path, f"test/data/{cdl_file}")

    # Attempt to split the file
    output_dir = tmp_path / "single_field"
    cmd = f"python splitnc.py {cmd_options} --output-dir {output_dir} {ncfile}"
    runcmd(cmd)

    # Check all the output files have one and only one fld_* variable
    for output_file in output_dir.glob("*.nc"):
        ds = xr.open_dataset(output_file, decode_times=xr.coders.CFDatetimeCoder(use_cftime=True))

        # Only one variable in each single-field file should match the field_regex
        count = 0
        for v in ds.variables:
            if re.match(field_regex, v):
                count += 1

        assert count == 1
