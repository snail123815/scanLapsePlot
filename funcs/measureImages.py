import numpy as np
import os
import re

from skimage import draw
from skimage.io import imread

from funcs import getScanTime, determineExtension


def measureImgs(path, measureType='centreDisk', polygons=[(0, 0, 1, 0, 0, 1), ], percentage=1.0, forceUseFileNumber=False, fileNumberTimeInterval=1) -> np.ndarray:
    """Measure all images in path\n
    Return a numpy array of shape (len(files), 2).\n

    Args:\n
        path (str): Path to the images folder\n
        measureType (str, optional): Define type of measurement. Defaults to 'centreDisk'. One of:\n
                measureTypes = [
                    'centreDisk', # Measure a circle with diameter is a percentage (percentage) of the image width
                    'square',     # Measure a square with the width is a percentage of the image width
                    'polygon'     # Measure a polygon. percentage will be ignored
                                  # TODO Extract polygon picture (max bonding box)
                ]\n
        polygon (tuple, optional): Affects type 'polygon'. (x1, y1, x2, y2, x3, y3 ...) Defaults to (0,0,1,0,0,1).\n
        percentage (float, optional): Affects type 'centreDisk' and 'square'.\n
                                      Percentage of the full width of the image, in range (0, 1].\n
                                      Defaults to 1.\n
        imgTimeDiff (float, optional): Affects when timing of images is not stored in the file system.\n
                                       Will judge base on the creation time of the first two images. If the first interval\n
                                       is less than 5 min (300 s), then I will assume the timing stored in the file (creation\n
                                       time) is not reliable and use the number in file names. This often caused by copying\n
                                       files and inappropriate image processing. \n
                                       Specify hours.\n
                                       Defaults to 1.\n
        maxNorm (bool, optional): When True, the average of the first 3 images are set to 0 (plus time0), all numbers will be\n
                                  normalised to this 0 and the maximum number. As a result, minus number can appear.\n
                                  Defaults to True.\n
        time0 (int, optional): Time of the first image, in hours. Defaults to 0.\n
        forceUseFileNumber (bool, optional): If True, the file creation time will be ignored. Defaults to False.\n

    Returns:\n
        np.array: shape = [len, 2], timings stored in the first column (hours), measured values stored in the second column.\n
    """
    extension = determineExtension(path)
    filePaths = sorted([os.path.join(path, file)
                        for file in os.listdir(path) if file.endswith(extension)])

    measureTypes = [
        'centreDisk',  # Measure a circle with diameter is a percentage (percentage) of the image width
        'square',     # Measure a square with the width is a percentage of the image width
        'polygon'     # Measure a polygon. percentage will be ignored
                      # TODO Extract polygon picture (max bonding box)
    ]
    assert measureType in measureTypes, f'{measureType} not accepted. ({", ".join(measureTypes)})'
    assert 0 < percentage <= 1.0, 'percentage should be in range (0, 1]'
    for polygon in polygons:
        assert len(polygon) >= 6 and len(polygon) % 2 == 0, f'polygon setup error (x1, y1, x2, y2, x3, y3 ...). At least 6, even number\n{polygon}'
    if len(polygons) == 1:  # expend
        polygons = polygons * len(filePaths)
    elif len(polygons) < len(filePaths):  # fill in with the last polygon tuple
        n = len(filePaths) - len(polygons)
        polygons += polygons[-1] * n
    assert len(polygons) == len(filePaths)

    # Determine if use file time or use 1 h as interval
    useFileTime = True
    if forceUseFileNumber:
        useFileTime = False
    else:
        times = [getScanTime(f) for f in filePaths[:2]]
        firstInterval = times[1] - times[0]
        if firstInterval < 300:
            useFileTime = False

    # Measurement: produce an array of times and an array of measured values
    data = np.zeros((len(filePaths), 2))
    for i, filePath in enumerate(filePaths):
        if useFileTime:
            time = getScanTime(filePath)/3600  # convert to hours
        else:
            file = os.path.split(filePath)[1]
            # Temove text before the last '_' (this should be subimages, the added posName needs removal)
            oriImgName = file.replace(file.split('_')[-1], '')[:-1]
            oriImgName = oriImgName.split('_cropped')[0] # when use cropped is true
            n = int(re.findall(r'[0-9]+', oriImgName)[-1])
            time = n * fileNumberTimeInterval
        im = imread(filePath, as_gray=True)
        if measureType == 'centreDisk':
            center = (tuple(a / 2 for a in im.shape))
            radius = im.shape[0] / 2 * percentage
            rr, cc = draw.disk(center, radius)
            roi = im[rr, cc]
        elif measureType == 'square':
            start = im.shape[0] / 2 * (1 - percentage)
            width = im.shape[0] * percentage
            rr, cc = draw.rectangle((start, start), extent=(width, width))
            roi = im[rr, cc]
        else:  # measureType == 'polygon'
            # rebase the polygon to the bonding box
            # polygon measured from imageJ MACRO
            polygon = np.array(polygons[i])
            polygon[::2] -= polygon[::2].min()
            polygon[1::2] -= polygon[1::2].min()
            rr, cc = draw.polygon(polygon[1::2], polygon[::2])
            roi = im[rr, cc]
        res = np.average(roi)
        data[i] = (time, res)

    return path, data  # path is needed as the sequence of multiprocessing is not preserved
