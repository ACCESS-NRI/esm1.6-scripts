#PBS -P rp23
#PBS -N remap_veg
#PBS -q normal
#PBS -l walltime=2:00:00
#PBS -l mem=8GB
#PBS -l ncpus=1
#PBS -l storage=gdata/rp23+gdata/xp65+gdata/p66+gdata/vk83+gdata/access
#PBS -l wd

module use /g/data/xp65/public/modules
module load conda/analysis3-25.08

reference_restart=""    # UM restart to use as a start point
restart_as_netcdf=""    # Intermediate NetCDF file to hold the CABLE relevant fields
new_vegetation_dist=""  # New vegetation distribution to substitute in
remap_config=""         # Config file to configure the remapping
remapped_restart_as_netcdf=""  # Remapped CABLE fields 
output_restart=""       # Name to write the new restart to

# Add the -s/--stash arguments to scripts 1 and 3 if you don't have access to the defaults, which are on gdata/access and gdata/rp23

python convert_UM_restart_to_netcdf.py -i ${reference_restart} -o ${restart_as_netcdf}
python adjust_restart_for_new_land_cover.py -i ${restart_as_netcdf} -o ${remapped_restart_as_netcdf} -m ${new_vegetation_dist} -c ${remap_config}
python add_netcdf_fields_to_UM_restart.py -i ${remapped_restart_as_netcdf} -o ${output_restart} -r ${reference_restart}
