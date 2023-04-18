from tiff_handler import TiffConverter
import os



def preprocess():
    source_path = 'sentinel_downloaded/'
    target_path = 'sentinel_preprocessed/'

    # copy all .tiff files from subfolders of source_path to target_path, and name them as subfolder.tiff
    for root, dirs, files in os.walk(source_path):
        for file in files:
            if file.endswith('.tiff'):
                # print(os.path.join(root, file))
                # print(os.path.join(root, file).split('/')[-2])
                os.system(f'cp {os.path.join(root, file)} {target_path}{os.path.join(root, file).split("/")[-2]}.tiff')


def merge():
    source_path = 'sentinel_preprocessed/'
    target_path = 'sentinel_merged/'

    # merge all .tiff files in target_path
    tiff_converter = TiffConverter(source_path)
    tiff_converter.reproject_merge()

    pass




# if run as a script
if __name__ == '__main__':
    # preprocess()
    
    # # calculate the duration of merge()
    import time
    start_time = time.time()
    merge() 
    print("--- %s seconds ---" % (time.time() - start_time))