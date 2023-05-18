from tiff_handler import TiffConverter
import os
import glob
import rasterio



def preprocess():
    source_path = 'sentinel_downloaded/'
    target_path = 'sentinel_preprocessed/'

    # get list of sub folders from source_path, order by folder creation time, ascending
    subfolders = [f.path for f in os.scandir(source_path) if f.is_dir()]
    subfolders.sort(key=lambda x: os.path.getmtime(x))

    # copy all .tiff files from subfolders of source_path to target_path, and name them as subfolder.tiff
    for subfolder in subfolders:
        # get all files in subfolder, and subfolder's subfolder,  recursively that ends with .tiff, and sort them by creation time, ascending
        files = []
        for root, dirs, subfiles in os.walk(subfolder):
            for file in subfiles:
                if file.endswith('.tiff'):
                    files.append(os.path.join(root, file))
        files.sort(key=lambda x: os.path.getmtime(x))

        
        #files = [f.name for f in os.scandir(subfolder) if f.is_file() and f.name.endswith('.tiff')]
        
        for file in files:
            if file.endswith('.tiff'):
                parent_folder = os.path.join(subfolder, file).split('/')[-3]

                src_path = os.path.join(subfolder, file)
                dst_path = f'{target_path}{parent_folder}/{os.path.join(subfolder, file).split("/")[-2]}.tiff'
                
                # create parent_folder if not exists
                if not os.path.exists(f'{target_path}{parent_folder}'):
                    os.makedirs(f'{target_path}{parent_folder}')

                os.system(f'cp {src_path} {dst_path}')


def get_images_order_by_gps_location(folder, num_images=10):
    # Get a list of all image files in the folder and its subfolders
    image_extensions = ('*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.tiff')
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(folder, '**', ext), recursive=True))

    # Get the creation time for each image
    image_files_with_gps = []
    for image in image_files:
        if 'EPSG3857' not in folder and 'EPSG3857' in image:
            continue
        if 'stitched' in image:
            continue
        with rasterio.open(image) as src:
            gps = src.bounds
            image_files_with_gps.append((image, gps))

    # Sort the images by creation time in descending order
    image_files_with_gps.sort(key=lambda x: (x[1].top, x[1].left), reverse=False)

    # Return the specified number of images
    return [x[0] for x in image_files_with_gps[:num_images]]

def merge_n(start, end):
    source_path = 'sentinel_preprocessed/001/'
    images = get_images_order_by_gps_location(source_path, end)
    short_image_names = [f.split('/')[-1] for f in images][start:end]
    tiff_converter = TiffConverter(source_path, short_image_names)
    tiff_converter.reproject_merge()
    pass

def merge_all():
    source_path = 'sentinel_preprocessed/'
    
    for subdir in os.listdir(source_path):
        if not os.path.isdir(os.path.join(source_path, subdir)):
            continue
        target_path = f'{source_path}{subdir}/'
        tiff_converter = TiffConverter(target_path)
        tiff_converter.reproject_merge()
        pass

    # # calculate the duration of merge()
    # import time
    # start_time = time.time()
    # merge() 
    # print("--- %s seconds ---" % (time.time() - start_time))


# if run as a script
if __name__ == '__main__':
    # preprocess()
    # merge_all()    
    # merge_n(76,86)    
    merge_n(0, 9)    
