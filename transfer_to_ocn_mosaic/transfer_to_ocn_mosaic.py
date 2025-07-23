# Copyright 2025 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

# =========================================================================================
# Script to update the ocean grid in ACCESS-ESM1.6 from FMS legacy to mosaic format. Areas
# at the North Pole are also corrected. It is intended that this script is only run once. It
# is retained in this repository only for reference and data provenance purposes.
#
# To run:
#   python transfer_to_ocn_mosaic.py --output-dir=<output-directory>
#
# The run command and full github url of the current version of this script is added to the
# metadata of the generated file. This is to uniquely identify the script and inputs used to
# generate the file. To produce files for sharing, ensure you are using a version of this script
# which is committed and pushed to github. For files intended for released configurations, use the
# latest version checked in to the main branch of the github repository.
#
# Contact:
#   Dougie Squire <dougie.squire@anu.edu.au>
#
# Dependencies:
#   netcdf4-python
#   esmgrids >= v0.1.2
#   FRE-NCtools >= v2024.05-1
# =========================================================================================

import os
import sys
from pathlib import Path
import subprocess
from netCDF4 import Dataset
import esmgrids
from esmgrids.mom_grid import MomGrid
from esmgrids.cice_grid import CiceGrid

path_root = Path(__file__).parents[1]
sys.path.append(str(path_root))

from scripts_common import get_provenance_metadata, md5sum

def copy_netcdf(src_file, dst_file):
    """Copy a netcdf file to a new location and return the new Dataset"""
    dst = Dataset(dst_file, "w")
    with Dataset(src_file) as src:
        # Copy global attributes
        dst.setncatts(src.__dict__)
        # Copy dimensions
        for name, dimension in src.dimensions.items():
            dst.createDimension(
                name, (len(dimension) if not dimension.isunlimited() else None))
        # Copy all variables
        for name, variable in src.variables.items():
            x = dst.createVariable(name, variable.datatype, variable.dimensions)
            # copy variable attributes all at once via dictionary
            dst[name].setncatts(src[name].__dict__)
            dst[name][:] = src[name][:]
    return dst

def main():
    parser = argparse.ArgumentParser(
        description="Update the ocean grid in ACCESS-ESM1.6 from FMS legacy to mosaic format."
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="The directory to write the output netcdf files.",
    )

    args = parser.parse_args()
    output_dir = Path(os.path.abspath(args.output_dir))

    curr_gspec = Path(
        "/g/data/vk83/configurations/inputs/access-esm1p5/modern/share/ocean/grids/mosaic/global.1deg/2020.05.19/grid_spec.nc"
    )
    curr_cgrids = Path(
        "/g/data/vk83/configurations/inputs/access-esm1p5/modern/share/coupler/grids/global.oi_1deg.a_N96/2020.05.19/grids.nc"
    )
    curr_careas = Path(
        "/g/data/vk83/configurations/inputs/access-esm1p5/modern/share/coupler/grids/global.oi_1deg.a_N96/2020.05.19/areas.nc"
    )
    
    # Get provenance metadata
    # --------------------------------------------
    this_file = os.path.normpath(__file__)
    metadata_history = get_provenance_metadata(
        this_file,
        f"python {os.path.basename(this_file)} --output-dir={output_dir}"
    )
    metadata_input_gspec = f"{curr_gspec} (md5 hash: {md5sum(curr_gspec)})"
    metadata_input_cgrids = f"{curr_cgrids} (md5 hash: {md5sum(curr_cgrids)})"
    metadata_input_careas = f"{curr_careas} (md5 hash: {md5sum(curr_careas)})"

    # Update ocean grid to mosaic format using FRE-NCtools `transfer_to_mosaic_grid` with
    # `--rotate_poly`
    # --------------------------------------------
    os.chdir(output_dir)
    run_cmd = f"transfer_to_mosaic_grid --input_file {str(curr_gspec)} --rotate_poly"
    subprocess.run(run_cmd, shell=True)

    # Clean up unneeded files
    remove_files = [
        "atmos_hgrid.nc",
        "atmos_mosaic.nc",
        "atmos_mosaicXland_mosaic.nc",
        "atmos_mosaicXocean_mosaic.nc",
        "land_hgrid.nc",
        "land_mosaic.nc",
        "land_mosaicXocean_mosaic.nc",
        "mosaic.nc"
    ]
    for f in remove_files:
        (output_dir / f).unlink()

    # Add provenance metadata to the output files
    for f in ["ocean_hgrid.nc", "ocean_mosaic.nc", "ocean_vgrid.nc", "topog.nc"]:
        output_file = output_dir / f
        with Dataset(output_file, "a") as ds:
            # Add history and input file metadata
            ds.history = metadata_history
            ds.inputFile = metadata_input_gspec
            ds.frenctools_version = FRENCTOOLS_VERSION

    # Create ocean_mask.nc from new topog.nc
    # --------------------------------------------
    # ocean_mask.nc is only needed for updating the CICE grid below
    with Dataset(output_dir / "topog.nc") as topog:
        depth = topog["depth"][:].data

    with Dataset(output_dir / "ocean_mask.nc", "w") as ocean_mask:
        ocean_mask.createDimension("ny", depth.shape[0])
        ocean_mask.createDimension("nx", depth.shape[1])
        mask = ocean_mask.createVariable(
            "mask",
            "i8",
            dimensions=("ny", "nx"),
            compression="zlib",
            complevel=1
        )
        mask.standard_name = "sea_binary_mask"
        mask[:] = (depth > 0).astype(int)
        ocean_mask.history = metadata_history
        ocean_mask.inputFile = metadata_input_gspec

    # Update CICE grid using `esmgrids`
    # --------------------------------------------
    cice_grid = CiceGrid.fromgrid(
        MomGrid.fromfile(
            output_dir / "ocean_hgrid.nc",
            mask_file=output_dir / "ocean_mask.nc"
        )
    )
    cice_grid.write(
        output_dir / "grid.nc",
        output_dir / "kmt.nc",
        metadata={
            "history": metadata_history,
            "inputFile": metadata_input_gspec,
            "esmgrids_version": f"{esmgrids.__version__}",
        },
        variant="cice5-auscom"
    )

    # Update coupler grids and areas
    # --------------------------------------------
    grids = copy_netcdf(curr_cgrids, output_dir / "grids.nc")
    grids["cice.lat"][:] = cice_grid.y_t
    grids["cice.lon"][:] = cice_grid.x_t
    grids["cice.ang"][:] = cice_grid.angle_t
    grids["cice.cla"][:] = cice_grid.clat_t
    grids["cice.clo"][:] = cice_grid.clon_t
    grids.history = metadata_history
    grids.inputFile = metadata_input_cgrids
    grids.close()

    areas = copy_netcdf(curr_careas, output_dir / "areas.nc")
    areas["cice.srf"][:] = cice_grid.area_t
    areas.history = metadata_history
    areas.inputFile = metadata_input_careas
    areas.close()


if __name__ == "__main__":
    import argparse

    # Load FRE-NCtools 2024.05-1
    # (https://github.com/ACCESS-NRI/FRE-NCtools/releases/tag/2024.05-1)
    # --------------------------------------------
    FRENCTOOLS_VERSION = "2024.05-1"
    moduleshome = os.environ.get('MODULESHOME', default=None)
    exec(open(Path(moduleshome) / "init/python.py").read())
    module("use", "/g/data/vk83/modules")
    module("load", f"fre-nctools/{FRENCTOOLS_VERSION}")

    main()