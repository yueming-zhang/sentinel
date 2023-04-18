import matplotlib.pyplot as plt
import numpy as np
import rasterio

tiff1 = '/mnt/e/ML.Data/geotiff/20230417/measurement/001.tiff'
tiff2 = '/mnt/e/ML.Data/geotiff/sentinel2_band4.tiff'
tiff3 = './examples/test_dir/4d34ca44cf5505abbf2690c928df83fe/response.tiff'

with rasterio.open(tiff3) as src:
    print ("Number of bands: ", src.count)
    print ("Width: ", src.width)
    print ("Height: ", src.height)
    print ("Bounds: ", src.bounds)
    print ("Coordinate reference system: ", src.crs)
    print ("Transform: ", src.transform)

    band1 = src.read(1)
