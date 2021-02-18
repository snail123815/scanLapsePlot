import os
from PIL import Image
from funcs import getScanTime

def crop(picPath, posDict, targetPaths, paddingPos=None, resizeFactor=None, useFileTime=True):
    picName, extension = os.path.splitext(os.path.basename(picPath))
    if extension not in ['.bmp', '.tif', '.tiff', '.png']:
        outputFmt = 'jpeg'
        outputExt = '.jpg'
        # no need to save as bmp for already lossy pictures
    else:
        outputFmt = 'bmp'
        outputExt = '.bmp'
        # bmp files will be easier for compression latter
    scanTime = getScanTime(picPath)
    atime, utime = (scanTime, scanTime)
    with Image.open(picPath) as im:
        iccProfile = im.info.get('icc_profile')
        for posName in posDict:
            targetPath = targetPaths[os.path.join('subImages', posName)]
            outFilePath = os.path.join(targetPath, f'{picName}_{posName}{outputExt}')
            im.crop(posDict[posName]).save(outFilePath,
                                           outputFmt,
                                           icc_profile=iccProfile,
                                           )
            if useFileTime:
                os.utime(outFilePath, (atime, utime))
        if paddingPos != None and not 'cropped_ori' in picPath:
            im = im.crop(paddingPos)
            # save cropped pictures
            croppedFilePath = os.path.join(targetPaths['cropped_ori'],
                                           f'{picName}_cropped{outputExt}')
            im.save(croppedFilePath, outputFmt, icc_profile=iccProfile)
            if useFileTime:
                os.utime(croppedFilePath, (atime, utime))
        if resizeFactor != None:
            resizeFilePath = os.path.join(targetPaths['resized'],
                                          f'{picName}_resized.jpg')
            newSize = tuple(int(size * resizeFactor) for size in im.size)
            im = im.resize(newSize)
            im.save(resizeFilePath,
                    'jpeg',
                    icc_profile=iccProfile,
                    progressive=True,
                    quality=85,
                    optimize=True)
            if useFileTime:
                os.utime(resizeFilePath, (atime, utime))
    return
# crop
