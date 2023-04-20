from sentinelhub import SHConfig
import datetime
import os
import numpy as np
from typing import Any, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np


from sentinelhub import (
    CRS,
    BBox,
    DataCollection,
    DownloadRequest,
    MimeType,
    MosaickingOrder,
    SentinelHubDownloadClient,
    SentinelHubRequest,
    bbox_to_dimensions,
)

from secret import client_id, client_secret

config = SHConfig()
config.sh_client_id = client_id
config.sh_client_secret = client_secret

def plot_image(
    image: np.ndarray, factor: float = 1.0, clip_range: Optional[Tuple[float, float]] = None, **kwargs: Any
) -> None:
    """Utility function for plotting RGB images."""
    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(15, 15))
    if clip_range is not None:
        ax.imshow(np.clip(image * factor, *clip_range), **kwargs)
    else:
        ax.imshow(image * factor, **kwargs)
    ax.set_xticks([])
    ax.set_yticks([])

betsiboka_coords_wgs84 = (46.16, -16.15, 46.51, -15.58)# interval_x = 0.35, interval_y = 0.57

evalscript_all_bands = """
    //VERSION=3
    function setup() {
        return {
            input: [{
                bands: ["B01","B02","B03","B04","B05","B06","B07","B08","B8A","B09","B10","B11","B12"],
                units: "DN"
            }],
            output: {
                bands: 13,
                sampleType: "FLOAT32"
            }
        };
    }

    function evaluatePixel(sample) {
        return [sample.B01,
                sample.B02,
                sample.B03,
                sample.B04,
                sample.B05,
                sample.B06,
                sample.B07,
                sample.B08,
                sample.B8A,
                sample.B09,
                sample.B10,
                sample.B11,
                sample.B12];
    }
"""

def download(betsiboka_coords_wgs84):
    resolution = 30
    betsiboka_bbox = BBox(bbox=betsiboka_coords_wgs84, crs=CRS.WGS84)
    betsiboka_size = bbox_to_dimensions(betsiboka_bbox, resolution=resolution)

    request_all_bands = SentinelHubRequest(
        data_folder="downloaded_data",
        evalscript=evalscript_all_bands,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L1C,
                time_interval=("2020-06-01", "2020-06-30"),
                mosaicking_order=MosaickingOrder.LEAST_CC,
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=betsiboka_bbox,
        size=betsiboka_size,
        config=config,
    )

    request_all_bands.save_data()

def download_images(start_index, end_index):
    for i in range(start_index, end_index):
        bbx = (betsiboka_coords_wgs84[0]+i%10*0.35, 
               betsiboka_coords_wgs84[1]+int(i/10)*0.57, 
               betsiboka_coords_wgs84[2]+i%10*0.35, 
               betsiboka_coords_wgs84[3]+int(i/10)*0.57)
        download(bbx)
        print('.', end='', flush=True)

download_images(136,200) #TODO: start from 36 to 100 to complete 002

