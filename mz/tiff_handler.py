import logging
import os

from os import listdir
from os.path import isfile, join
from pathlib import Path
from typing import List
import time

import numpy as np
import rasterio
from rasterio.crs import CRS
import rasterio.merge

# from inference.sentinel_batch_data_retrieval.post_process.project_shape_handler import ProjectShape
from rasterio.fill import fillnodata
from rasterio.io import DatasetReader
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, calculate_default_transform, reproject

logger = logging.getLogger()


class TiffConverter:
    """Loads raster tiff files from local, these and then be converted to common EPSG and merged."""

    def __init__(self, path: str) -> None:
        """Inits the converter and find's all tiffs in the path."""
        self.path = path
        self.all_files = [f for f in listdir(self.path) if isfile(join(self.path, f))]
        self.tiff_files = [i for i in self.all_files if i.split(".")[-1] == "tiff"]
        self.reporjected_tiff_paths: List[str] = []
        self.CRS_list = self._crs_list()
        self.CRS_set = self._crs_set()

    def n_cores(self, free: int = 1) -> int:
        """Gets number of cores to use for multiprocessing tasks while leaving one free."""
        system_cores = os.cpu_count()
        if not system_cores:
            return 1
        cores = int(system_cores) - free
        return max(1, cores)

    def add_path(self, files: List[str], add_path: bool = False) -> List[str]:
        """Adds the tiff working directory path to filename list."""
        if add_path:
            return [f"{self.path}{f}" for f in files]
        return files

    def _crs_list(self, add_path: bool = False) -> List[str]:
        """Lists the crs of all tiff files."""
        files = [rasterio.open(self.path + f).crs for f in self.tiff_files]
        return self.add_path(files, add_path)

    def _crs_set(self, add_path: bool = False) -> List[str]:
        """Creates a set of the crs list."""
        files = list(set(self.CRS_list))
        return self.add_path(files, add_path)

    def open_rasters(self) -> List[DatasetReader]:
        """Opens all raster files in the class target path."""
        return [rasterio.open(i) for i in self.add_path(self.tiff_files)]

    @staticmethod
    def path_to_repojected_path(path: str, crs_name: str) -> str:
        """Parses data source path to the re-projected tiff files."""
        crs_name = "".join(filter(str.isalnum, crs_name))
        split_path = path.split("/")
        return f"{'/'.join(split_path[:-1])}/{crs_name}/{split_path[-1]}"

    @staticmethod
    def ensure_path(path: str, last_is_file: bool = False) -> None:
        """Ensures path with parents, and exists ok. Can remove the last element ie the filename."""
        if last_is_file:
            path = "/".join(path.split("/")[:-1])
        Path(path).mkdir(parents=True, exist_ok=True)

    def reproject_raster(self, path: str, dst_crs: str = "EPSG:3857") -> None:
        """Re-projects a tiff raster file to new EPSG and saves to a directory named after tha EPSG in the source directory."""
        dest_path = self.path_to_repojected_path(path, dst_crs)
        self.reporjected_tiff_paths.append(dest_path)
        self.ensure_path(dest_path, True)

        with rasterio.open(path) as src:
            dst_transform, width, height = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *src.bounds
            )
            kwargs = src.meta
            kwargs["transform"] = dst_transform
            kwargs["height"] = height
            kwargs["width"] = width
            kwargs["crs"] = dst_crs
            data = src.read()
            channels = src.count

            with rasterio.open(dest_path, "w", **kwargs) as dst:
                dest = np.zeros((channels, height, width))
                reproject(
                    data,
                    dest,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest,
                    init_dest_nodata=True,
                    num_threads=self.n_cores(),
                    **{"UNIFIED_SRC_NODATA": "xx", "SOURCE_EXTRA": 0},  # Remove this line?
                )
                dst.write(dest)

    def _reporject_raster_files(self, dst_crs: str = "EPSG:3857") -> None:
        """Re-projects all rasters in the classes target data path."""
        paths = self.add_path(self.tiff_files, True)
        for path in paths:
            self.reproject_raster(path, dst_crs)

    def _merge_tiff_list(self, paths: List[str]) -> Path:  # -> Tuple[NDArray, Affine]: (merged_data, _out_transform)
        """Merges all files in given list regardless of EPSG."""
        self.dst_path = Path("/".join(paths[0].split("/")[:-1]))
        logger.info(f"merging rasters to {self.dst_path}")

        dst_file = self.dst_path / "stitched.tif"
        rasterio.merge.merge(
            paths,
            dst_path=dst_file,
            target_aligned_pixels=False,
            resampling=Resampling.nearest,
        )
        return dst_file

    def reproject_merge(self, dst_crs: str = "EPSG:3857") -> Path:
        """Calls both reproject and merge functions in one go."""

        # calculate duration of each step
        start = time.time()
        self._reporject_raster_files(dst_crs)
        end = time.time()
        print(f"reprojecting rasters took {end - start} seconds", flush=True)
        dst_file = Path(self._merge_tiff_list(self.reporjected_tiff_paths))
        end1 = time.time()
        print(f"merging rasters took {end1 - end} seconds", flush=True)
        return dst_file

    # def clip_image_to_project(self, project_shape: ProjectShape) -> Path:
    #     """Clips stitched image down to the size of the project."""
    #     src_path = self.dst_path / "stitched.tif"
    #     dst_path = self.dst_path / "stitched_clipped.tif"

    #     logger.info(f"clipping raster to {dst_path}")

    #     with rasterio.open(src_path) as src:
    #         wsen_bounds, width, height = project_shape.project_bound_box_width_height(src=src, round_up_to_multiple=64)
    #         dst_transform, _, _ = calculate_default_transform(src.crs, src.crs, src.width, src.height, *src.bounds)
    #         w, s, e, n = wsen_bounds

    #         channels = src.count
    #         bound_transform = from_bounds(w, s, e, n, width, height)

    #         kwargs = src.meta
    #         kwargs["transform"] = bound_transform
    #         kwargs["height"] = height
    #         kwargs["width"] = width

    #         data = src.read()

    #         with rasterio.open(dst_path, "w", **kwargs) as dst:
    #             dest = np.zeros((channels, int(height), int(width)))
    #             reproject(
    #                 data,
    #                 dest,
    #                 src_transform=src.transform,
    #                 src_crs=src.crs,
    #                 dst_transform=bound_transform,
    #                 dst_crs=src.crs,
    #                 resampling=Resampling.nearest,  # bilineaR
    #                 init_dest_nodata=True,
    #             )

    #             na_mask = dest[1] != 0
    #             for ix in range(channels):
    #                 fillnodata(image=dest[ix], mask=na_mask, max_search_distance=2, smoothing_iterations=0)

    #             dst.write(dest)
    #     return dst_path
