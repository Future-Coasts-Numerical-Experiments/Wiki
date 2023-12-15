"""
created matt_dumont 
on: 16/12/23
"""
from pathlib import Path
import netCDF4 as nc
import pandas as pd
import numpy as np
import datetime

base_crs_atts = {'grid_mapping_name': "transverse_mercator",
                 'scale_factor_at_central_meridian': 0.9996,
                 'longitude_of_central_meridian': 173.0,
                 'latitude_of_projection_origin': 0.0,
                 'false_easting': 1600000,
                 'false_northing': 10000000,
                 'epsg': 2193}


def initialize_dataformat(outpath, x, y, description, author, script, version,
                          depth=None, slr_increment=None, real=None, ):
    """
    make a basic netcdf file for future coasts  x,y data and a crs object so the nc can be viewed in
    GIS systems note that the depth dimension uses the zero indexed integer values for the layers

    :param outpath: path to the new file, will be overwritten
    :param x: 1d array of x values (nztm)
    :param y: 1d array of y values (nztm)
    :param description: a description to add to the netcdf file attributes(.description)
    :param author: author name to add to the netcdf file attributes(.author)
    :param script: script name to add to the netcdf file attributes(.script)
    :param version: version number to add to the netcdf file attributes(.version)
    :param depth: 1d array of depth values (m), optional
    :param slr_increment: 1d array of sea level rise increments (m), optional
    :param real: 1d array of realisation numbers, optional note -1 is used as a missing value
    :return: open, writable netcdf file
    """

    outfile = nc.Dataset(outpath, 'w')
    # create dimensions
    outfile.createDimension('nztmy', len(y))
    outfile.createDimension('nztmx', len(x))

    proj = outfile.createVariable('crs', 'i1')
    proj.setncatts({'grid_mapping_name': "transverse_mercator",
                    'scale_factor_at_central_meridian': 0.9996,
                    'longitude_of_central_meridian': 173.0,
                    'latitude_of_projection_origin': 0.0,
                    'false_easting': 1600000,
                    'false_northing': 10000000,
                    'epsg': 2193,
                    'units': 'None',
                    'long_name': 'NZTM2000 / New Zealand Transverse Mercator 2000 CRS',
                    'missing_value': 0,
                    'description': 'This variable is used by Qgis and Arcgis to define the projection of the data.'
                    })

    lat = outfile.createVariable('nztmy', 'f8', ('nztmy',), fill_value=np.nan)
    lat.setncatts({'units': 'm',
                   'long_name': 'Northing in New Zealand Transverse Mercator',
                   'missing_value': np.nan,
                   'standard_name': 'projection_y_coordinate'})
    lat[:] = y

    lon = outfile.createVariable('nztmx', 'f8', ('nztmx',), fill_value=np.nan)
    lon.setncatts({'units': 'm',
                   'long_name': 'Easting in New Zealand Transverse Mercator',
                   'missing_value': np.nan,
                   'standard_name': 'projection_x_coordinate'})
    lon[:] = x

    if depth is not None:
        outfile.createDimension('depth', len(depth))
        # create variables
        d = outfile.createVariable('depth', 'f8', ('depth',), fill_value=np.nan)
        d.setncatts({'units': 'm',
                         'long_name': 'depth from ground surface',
                         'missing_value': np.nan})
        d[:] = depth

    if slr_increment is not None:
        outfile.createDimension('slr_increment', len(slr_increment))
        slr = outfile.createVariable('slr_increment', 'f8', ('slr_increment',), fill_value=np.nan)
        slr.setncatts({
            'units': 'm',
            'long_name': 'Sea level rise increment',
            'missing_value': np.nan
        })

    if real is not None:
        assert pd.api.types.is_integer_dtype(real), 'real must be an integer array'
        assert -1 not in real, 'real cannot contain -1, it is the missing value'
        outfile.createDimension('real', len(real))
        r = outfile.createVariable('real', int, ('real',), fill_value=-1)
        r.setncatts({
            'units': 'None',
            'long_name': 'realisation number',
            'missing_value': -1
        })

    # set global attributes
    outfile.description = description
    outfile.date = '{}'.format(datetime.datetime.now().isoformat())
    outfile.author = author
    outfile.script = script
    outfile.version = version

    return outfile


def check_netCDF_format(nc_file, log_path=None, raise_error=True):
    """
    check the netcdf file format to ensure it matches the expected format
    :param nc_file: path to the netcdf file
    :param log_path: path to a log file to write the problems to or None (no log file, errors printed to stout)
    :param raise_error: if True raise an error if the file does not match the expected format
    :return: True if the file matches the expected format
    """
    problems = []
    with nc.Dataset(nc_file, 'r') as nc_file:

        # check the dimensions
        for dim in ['nztmy', 'nztmx']:
            if dim not in nc_file.dimensions:
                problems.append('{} dimension is missing'.format(dim))

        # check for essential dimension variables
        for k in nc_file.dimensions:
            if k not in nc_file.variables:
                problems.append(f'{k} variable is missing for dimension {k}')

        # check variable attributes
        for k in nc_file.variables:
            expect_atts = ['units', 'long_name', 'missing_value']
            atts = nc_file.variables[k].ncattrs()
            for a in expect_atts:
                if a not in atts:
                    problems.append(f'{k} variable is missing attribute {a}')

        # check CRS variable
        if not 'crs' in nc_file.variables:
            problems.append('crs variable is missing')
        crs_atts = nc_file['crs'].ncattrs()
        for k, v in base_crs_atts.items():
            if k not in crs_atts:
                problems.append(f'crs variable is missing attribute {k}')
            elif nc_file['crs'].getncattr(k) != v:
                problems.append(f'crs variable has incorrect value for attribute {k}')

        # check for file level attributes
        expect_file_atts = ['description', 'date', 'author', 'script', 'version']
        file_atts = nc_file.ncattrs()
        for a in expect_file_atts:
            if a not in file_atts:
                problems.append(f'file is missing attribute {a}')
    if len(problems) > 0:
        if log_path is not None:
            with open(log_path, 'w') as log:
                log.write(f'netcdf file does not match the expected format: {nc_file}\n  * ')
                log.write('\n  * '.join(problems))
        else:
            print('\n\n **** netcdf file does not match the expected format ****\n  * ')
            print('\n  * '.join(problems))
        if raise_error:
            raise ValueError('netcdf file does not match the expected format')
        else:
            return False
    return True


def make_example_file():
    temp_path = Path.home().joinpath('Downloads', 'ex_fut.nc')
    x = np.arange(0, 100, 10)
    y = np.arange(200, 400, 10)
    depth = np.arange(0, 10, 1)
    slr = np.arange(0, 10, 1)
    real = np.arange(0, 10, 1)
    nc_file = initialize_dataformat(temp_path, x, y,
                                    description='test file',
                                    author='matt dumont',
                                    script=__file__,
                                    version='v0.1', depth=depth, slr_increment=slr,
                                    real=real)
    nc_file.close()
    check_netCDF_format(temp_path, raise_error=True)

if __name__ == '__main__':
    make_example_file()