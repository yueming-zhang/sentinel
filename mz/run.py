import logging
import sys

from multiprocessing import Pool
from pathlib import Path
from typing import List, Tuple, Union

from citools.aws.s3 import BucketRepository
from inference.sentinel_batch_data_retrieval.config import Config
from inference.sentinel_batch_data_retrieval.post_process.project_shape_handler import ProjectShape
from tiff_handler import TiffConverter
from inference.sentinel_batch_data_retrieval.post_process.tile_area import AreaTile
from retry import retry
from tqdm import tqdm

config = Config()
settings = config.get_settings()

Path(config.DATA_DIR).mkdir(parents=True, exist_ok=True)
Path(config.LOGGING_DIR).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(f"{config.LOGGING_DIR}/raw_processing_logfile.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logging.getLogger("boto").setLevel(logging.INFO)
logging.getLogger("botocore").setLevel(logging.CRITICAL)
logging.getLogger("rasterio").setLevel(logging.CRITICAL)
logging.getLogger("Warning 1").setLevel(logging.CRITICAL)


def find_all_projects_from_bucket(bucket_str: str) -> List[str]:
    """Gets first level directories from S3."""
    bucket = BucketRepository(bucket_str)  # config.SENTINEL_HUB_DATA_BUCKET)
    return [i.split("/")[0] for i in bucket.find_directory_keys_by_key("")]


def project_dates_raw_sentinel_data(
    bucket_str: str, project: str, if_filename_starts: str = "result-"
) -> List[Tuple[str, ...]]:
    """Find all dates for the given project, None is all directories."""
    bucket = BucketRepository(bucket_str)  # config.SENTINEL_HUB_DATA_BUCKET)
    project_dates = bucket.find_directory_keys_by_key(f"{project}/")

    download_project_dates: List[str] = []
    for project_date in project_dates:
        project_date_files = bucket.find_object_keys_by_key(f"{project_date}")
        project_date_files = [f.split("/")[-1] for f in project_date_files]
        result_files: List[str] = [f for f in project_date_files if f.startswith(if_filename_starts)]
        if result_files:  # TODO: rename to generic and add looks for file to current
            download_project_dates.append(project_date)
    return [tuple(i[:-1].split("/")) for i in download_project_dates]


def rmdir(directory_str: Union[Path, str]) -> None:
    """Rmdir recursively."""
    directory = Path(directory_str)
    for item in directory.iterdir():
        if item.is_dir():
            rmdir(item)
        else:
            item.unlink()
    directory.rmdir()


@retry(tries=3, delay=2)
def upload_to_s3(bucket: BucketRepository, to_path: str, local_from_path: str) -> None:
    """Wrapper to upload files to s3 with retry."""
    bucket.upload_file_by_key(to_path, Path(local_from_path))


def try_upload_to_s3(bucket: BucketRepository, to_path: str, local_from_path: str) -> None:
    """Try with a retry 3 times to prevent error."""
    try:
        upload_to_s3(bucket, to_path, local_from_path)
    except Exception as e:
        pass
        logging.info(f"Couldn't upload to s3:   {e}")


def process_project_date(project_key: str, dated_key: str) -> None:
    """Downloads raw tile data from S3 SH bucket and processes into a reprojected, stitched, clipped to project size tiff."""
    project_date_key = f"{project_key}/{date_key}/"
    local_project_data_dir = f"{config.DATA_DIR_SATELLITE}/{project_key}/"
    local_project_date_data_dir = f"{config.DATA_DIR_SATELLITE}/{project_date_key}"

    Path(config.DATA_DIR_SATELLITE).mkdir(parents=True, exist_ok=True)

    sentinel_bucket = BucketRepository(config.SENTINEL_HUB_DATA_BUCKET)
    ai_data_bucket = BucketRepository(config.CERES_AI_DATA_BUCKET)

    if not Path(local_project_date_data_dir).exists() and True:
        logging.info(f"Downloading to {local_project_date_data_dir}")
        sentinel_bucket.download_directory_by_key(project_date_key, Path(local_project_data_dir))

    project = ProjectShape(project_key, **settings["ProjectS3Settings"])
    project.convert_epsg("EPSG:3857")

    tiff_data = TiffConverter(local_project_date_data_dir)
    tiff_data.reproject_merge("EPSG:3857")
    clipped_image_path = tiff_data.clip_image_to_project(project)

    area_tile = AreaTile(clipped_image_path, project)
    subtile_csv_path = area_tile.save_subtiles_csv(local_project_date_data_dir)
    subtile_data_path = area_tile.save_subtiles_data(local_project_date_data_dir)

    logging.info(f"Uploading {clipped_image_path}, {subtile_csv_path}, {subtile_data_path}")

    try_upload_to_s3(ai_data_bucket, project_date_key + clipped_image_path.name, clipped_image_path)
    try_upload_to_s3(ai_data_bucket, project_date_key + subtile_csv_path.name, subtile_csv_path)
    try_upload_to_s3(ai_data_bucket, project_date_key + subtile_data_path.name, subtile_data_path)

    logging.info(f"Purging {local_project_date_data_dir}")
    rmdir(local_project_date_data_dir)  # local_project_date_data_dir


if __name__ == "__main__":
    projects = find_all_projects_from_bucket(config.SENTINEL_HUB_DATA_BUCKET)

    downloaded_project_dates = []
    for project_name_downloaded in tqdm(projects, desc="Checking Already Downloaded Dates For Projects"):
        downloaded_project_dates.extend(
            project_dates_raw_sentinel_data(config.SENTINEL_HUB_DATA_BUCKET, project_name_downloaded)
        )

    processed_project_dates: List[Tuple[str, ...]] = []
    for project_name_processed in tqdm(projects, desc="Checking Already Processed Dates For Projects"):
        processed_project_dates.extend(
            project_dates_raw_sentinel_data(
                config.CERES_AI_DATA_BUCKET, project_name_processed, if_filename_starts="stitched_clipped"
            )
        )

    to_process_project_dates = [i for i in downloaded_project_dates if i not in processed_project_dates]
    # to_process_project_dates.reverse()

    logging.info(f"downloaded_project_dates: {len(downloaded_project_dates)}")
    logging.info(f"processed_project_dates: {len(processed_project_dates)}")
    logging.info(f"to_process_project_dates: {len(to_process_project_dates)}")

    # for project_key, date_key in tqdm(to_process_project_dates):
    #    logging.info(f"###  Starting process for project: {project_key} and date: {date_key}  ###")
    #    process_project_date(project_key, date_key)

    with Pool(5) as p:
        p.starmap(process_project_date, to_process_project_dates)

    logging.info("done for now :)")
