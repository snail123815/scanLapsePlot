import traceback
import os
import pickle
import argparse
import hashlib
import sys
from datetime import datetime
from shutil import copy2, copytree, rmtree
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from funcs import crop, getPositions, createFolders, getPosToCrop
from funcs import getInfo, measureImgs, plotMeasured, changeFileName
from funcs.changeName import genLogFile  # To get old file name when parsing multiple location data using old file name as reference


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description='')
    parser.add_argument('rootPath', help='Path to process, with original_images dir')
    parser.add_argument('sampleInfoTsvPath',
                        help='tsv file for sample information, same name will be averaged, when multiple location files are needed, use the first one for this mandatory argument')
    parser.add_argument('--normType', choices=['None', 'Each', 'Combined'], default='Combined',
                        help="Specify how the normalisation is done",)
    parser.add_argument('--endTiming', type=float,
                        help="The time of the last picture to plot, in hours")
    parser.add_argument('--percentage', default=1.0, type=float,
                        help='This precent is to specify the precentage of the picture width to be considered')
    parser.add_argument('-r', '--resizeFactor', type=float, default=0.35, metavar='FLOAT',
                        help='Factor of original size (0-1), default 0.35')
    parser.add_argument('--noTimeFromFile', action='store_true',
                        help='Time from original file will be stored in all new files if this is not set')
    parser.add_argument('--locationFromCropped', action='store_true',
                        help='Set if the locations are measured from images in "cropped_ori" folder. Will only take effect if "original_images" folder is gone.')
    parser.add_argument('--forceNoFillBetween', action='store_true',
                        help='fill between stderr if not set')
    parser.add_argument('--imageInterval', default=1.0, type=float,
                        help='Hours, only affect if --noTimeFromFile is set or the creation time cannot be obtained from file')
    parser.add_argument('--startImageTiming', type=float, default=0.,
                        help="The timing of the first picture, in hours")
    parser.add_argument('--reExtract', action='store_true',
                        help='Force re-extract pictures')
    parser.add_argument('--reMeasure', action='store_true',
                        help='Force re-measure')
    parser.add_argument('--diffPos', nargs='*',
                        help='''If your plates was moved during experiment, then you need multiple
                        position files.
                        This argument allows you to do:
                        [start file] [positionTsvPath] [start file] [positionTsvPath]...
                        DO NOT add the first file (start from 0) again.
                        The START FILE is the file name of the original file name. Check the log file for the old name.
                        ''')

    args = parser.parse_args()
    rootPath = args.rootPath.strip()
    sampleInfoTsvPath = args.sampleInfoTsvPath.strip()
    resizeFactor = args.resizeFactor
    locFromCropped = args.locationFromCropped
    forceNoFillBetween = args.forceNoFillBetween
    noTimeFromFile = args.noTimeFromFile
    imageInterval = args.imageInterval
    normType = args.normType
    startImageTiming = args.startImageTiming
    timeZ = args.endTiming
    percentage = args.percentage
    reExtract = args.reExtract
    reMeasure = args.reMeasure
    diffPos = args.diffPos

    # convert to realpath in case of failure in some systems 1/2
    rootPath = os.path.realpath(rootPath)

    assert os.path.isdir(rootPath), f'rootPath {rootPath} does not exist.'

    # Get file names to crop
    renameLogFile = genLogFile(rootPath)
    if not os.path.isfile(renameLogFile):
        changeFileName(rootPath, reverse=False)
    oldFiles, newFiles = ([], [])
    with open(renameLogFile, 'rb') as f:
        dictOld2New, _, _ = pickle.load(f)
    for of in dictOld2New:
        oldFiles.append(of)
        newFiles.append(dictOld2New[of])
    # sort oldFiles based on newFiles
    oldFiles = [f for _, f in sorted(zip(newFiles, oldFiles))]
    # sort newFIles after oldFiles is sorted
    newFiles.sort()

    # If the targets moved during time lapse experiment, you might need to specify different
    # metadata files for the moved location
    diffPosNums = [0, ]
    diffPosFiles = [sampleInfoTsvPath, ]
    diffPosFileHashes = []
    if diffPos != None:
        if len(diffPos) % 2 != 0:
            parser.error('The --diffPos argument requires both number and file')
        # PARSE args
        for imgfile, posFile in zip(diffPos[0::2], diffPos[1::2]):
            if imgfile in oldFiles:
                idx = oldFiles.index(imgfile)
            elif imgfile in newFiles:
                idx = newFiles.index(imgfile)
            else:
                raise ValueError(f'File {imgfile} missing from the original file names ({oldFiles[:5]}...) ({newFiles[:5]}...)')
            diffPosNums.append(oldFiles.index(imgfile))
            diffPosFiles.append(posFile)
    # convert to realpath in case of failure in some systems 2/2
    diffPosFiles = [os.path.realpath(f) for f in diffPosFiles]
    for f in diffPosFiles:
        assert os.path.isfile(f), f'sample information table {f} does not exist.'
        sha1 = hashlib.sha1()
        with open(f, 'rb') as f:
            sha1.update(f.read())
            diffPosFileHashes.append(sha1.hexdigest())

    # correct names can be found in the pickled log file)
    useCroppedImg = False
    imgPath = os.path.join(rootPath, 'original_images')
    if not os.path.isdir(imgPath):
        imgPath = os.path.join(rootPath, 'cropped_ori')
        print(f'original_images folder not found, use cropped_ori folder for source images')
        assert os.path.isdir(imgPath), f'cropped_ori folder not found in {rootPath}.'
        useCroppedImg = True

    # Compare hashes with previously runs, extract pictures again if not the same
    # Also consider reExtract argument
    posFileHashesFile = os.path.join(rootPath, 'Hashes for last measurement metadata files'.replace(' ', '_'))
    doExtractPics = True
    extractArgsStatic = [diffPosFileHashes, useCroppedImg, locFromCropped, diffPos]
    if os.path.isdir(os.path.join(rootPath, 'subImages')) and os.path.isfile(posFileHashesFile) and not reExtract:
        with open(posFileHashesFile, 'rb') as f:
            try:
                extractArgsStatic_old = pickle.load(f)
                if extractArgsStatic_old == extractArgsStatic:
                    doExtractPics = False
            except:
                pass
    if doExtractPics:
        with open(posFileHashesFile, 'wb') as f:
            pickle.dump(extractArgsStatic, f)
        reMeasure = True

    # Generate file paths to process
    if useCroppedImg:
        fns_exts = [os.path.splitext(f) for f in newFiles]
        newFiles = [f'{n[0]}_cropped{n[1]}' for n in fns_exts]
    fileList = [os.path.join(imgPath, f) for f in newFiles]

    # Get positions from the first metadata file
    posDict = getPositions(diffPosFiles[0])
    posToCrop = getPosToCrop(posDict, useCroppedImg, locFromCropped)
    paddingPos = posDict['removePadding']['paddingPos']  # Should equal to None when remove padding is not specified
    # Create folder for each sample (posName)
    targetPaths = {}
    folders = [os.path.join('subImages', f) for f in list(posToCrop.keys())]

    # Add additional folder for cropped and resized pictures
    # Resized folder will store resized cropped images
    if paddingPos != None and not useCroppedImg:
        folders.append('cropped_ori')
    folders.append('resized')

    assert len(set(folders)) == len(folders), f'There are duplications in the sample IDs:\n{[i for i in folders if folders.count(i) > 1]}'

    # See if the previous picture extraction has resulted any file (avoid empty measurment)
    firstSubFolder = os.path.join(rootPath,folders[0])
    if os.path.isdir(firstSubFolder):
        if not len(os.listdir(firstSubFolder)) > 2:
            doExtractPics = True
        pass

    ################# EXTRACT PICTURES #########################################################

    if doExtractPics:
        print('Clearing existing folders...')
        for p, _, _ in os.walk(rootPath):
            if p == rootPath:
                continue
            dname = os.path.split(p)[-1]
            if dname.startswith('result_'):
                continue
            if dname == 'original_images':
                continue
            if dname == 'cropped_ori' and useCroppedImg == True:
                continue
            try:
                rmtree(p)
            except FileNotFoundError:
                pass
        print('Creating folders...')
        targetPaths = createFolders(rootPath, folders, reset=True)

        for i, (num, sampleInfoTsvPath) in enumerate(zip(diffPosNums, diffPosFiles)):
            try:
                nextGroupStart = diffPosNums[i + 1]
            except IndexError:
                nextGroupStart = len(fileList)

            if i != 0:
                posDict = getPositions(sampleInfoTsvPath)
                posToCrop = getPosToCrop(posDict, useCroppedImg, locFromCropped)
            # Prepare cropping files
            print(f'Cropping group {i+1}/{len(diffPosNums)}...')
            subFileList = fileList[diffPosNums[i]:nextGroupStart]
            # RUN. Submit cropping threads
            filePathList = [os.path.join(imgPath, file) for file in subFileList]
            threadPool = ThreadPoolExecutor(max_workers=os.cpu_count())
            futures = []
            for i, file in enumerate(filePathList):
                future = threadPool.submit(
                    crop, file, posToCrop, targetPaths,
                    paddingPos=paddingPos,
                    resizeFactor=resizeFactor,
                    useFileTime=not noTimeFromFile,
                )
                print(f'Submitted {i}: {os.path.split(file)[-1]}')
                if i == 0:
                    exception = future.exception()
                    # this will wait the first implementation to finish, and check if
                    # any exception happened
                    if exception != None:
                        print('There is exception in the first implementation:')
                        traceback.print_tb(exception.__traceback__)
                        print(exception.__class__, exception)
                        exit()
                futures.append(future)
            print('All images submitted for cropping and creating subimages! Waiting for finish.')
            exceptions = [future.exception() for future in futures]
            for i, exception in enumerate(exceptions):
                if exception != None:
                    print(f'There is exception in run index {i}:')
                    traceback.print_tb(exception.__traceback__)
                    print(type(exception), exception)
                    break
            threadPool.shutdown()
        print('Finished!')

    # Check if dataFile exists and arguments are the same as previous
    measureArgsStatic = [diffPosNums, diffPosFileHashes, noTimeFromFile, imageInterval, startImageTiming, normType, percentage]
    allPicsData = pd.DataFrame()
    measure = True
    dataPickle = os.path.join(rootPath, 'data.pickle')
    if not reMeasure and os.path.isfile(dataPickle):
        if os.stat(dataPickle).st_size > 0:
            with open(dataPickle, 'rb') as resultData:
                oldAllPicsData, measureArgsStatic_old = pickle.load(resultData)
                if measureArgsStatic_old == measureArgsStatic:  # arguments affect measured data
                    measure = False
                    allPicsData = oldAllPicsData

    sampleInfo = getInfo(diffPosFiles[0])  # will be used in both measurement and plotting
    ################# EXTRACT PICTURES DONE #########################################################

    ################# MEASUREMENT #########################################################

    if measure:

        threadPool = ThreadPoolExecutor(max_workers=8)
        futures = []

        for folder in sampleInfo:
            measureType = sampleInfo[folder]['measure']
            assert measureType in ['centreDisk', 'square', 'polygon'], \
                f'Error found in sample information file, "measure" should be in [\'centreDisk\', \'square\', \'polygon\'], {measureType} found.'

            polygons = [(0, 0, 1, 0, 0, 1), ]  # polygon initiation for non-polygon measurments
            if measureType == 'polygon':  # needs to go back to posDict to find location

                # Generate polygon locations
                polygons = []  # reset this to start with 0
                for i, (num, sampleInfoTsvPath) in enumerate(zip(diffPosNums, diffPosFiles)):
                    try:
                        nextGroupStart = diffPosNums[i + 1]
                    except IndexError:  # reach the end
                        nextGroupStart = diffPosNums[i] + 1
                    posDict = getPositions(diffPosFiles[0])
                    polygon = posDict['Polygon_poly'][folder]
                    n = nextGroupStart - num
                    polygons.extend([polygon] * n)

            # Submit measurement to thread pool
            future = threadPool.submit(
                measureImgs,
                os.path.join(rootPath, 'subImages', folder),
                measureType,
                polygons=polygons,
                percentage=percentage,
                forceUseFileNumber=noTimeFromFile,
                fileNumberTimeInterval=imageInterval
            )
            futures.append(future)
            print(f'Submitted {folder} for greyness measurement.')

        # Exception handle
        exceptions = [future.exception() for future in futures]
        for i, excep in enumerate(exceptions):
            if excep != None:
                print(f'There is exception in run index {i}:')
                print(excep)
                break

        threadPool.shutdown()  # wait for every thread to complete

        # get results
        for future in futures:
            path, data = future.result()
            posName = os.path.split(path)[-1]
            # data processing according to arguments

            # rebase time to the first picture (if 3 (hours), then the data will start with 3)
            # Now the data should be actual hours (after the experimental time zero)
            data[:, 0] -= (data[:, 0].min() - startImageTiming)
            # sort on time
            timeSort = np.argsort(data[:, 0])
            data = data[timeSort, :]
            # Normalization
            if normType == 'Each':
                # use first 3 hours data as zero point
                zeroPoint = data[:3, 1].mean()
                values = data[:, 1] - zeroPoint
                data[:, 1] = values/values.max()

            # Put into data frame
            toDf = pd.DataFrame(data[:, 1], index=data[:, 0], columns=[posName])
            allPicsData = pd.concat((allPicsData, toDf), axis=1)

        if normType == 'Combined':
            min = allPicsData.iloc[:3].values.mean()  # will convert to nparray and calculate mean of everything
            values = allPicsData.values - min
            newData = values/values.max()
            # put data back
            allPicsData = pd.DataFrame(newData, index=allPicsData.index, columns=allPicsData.columns)

        with open(dataPickle, 'wb') as resultData:
            pickle.dump([allPicsData, measureArgsStatic], resultData)
        allPicsData.to_excel(f'{os.path.splitext(dataPickle)[0]}.xlsx')
    ################# MEASUREMENT DONE #########################################################

    ################# PLOTTING #########################################################

    # groupSequence = [2, 5]  # index of original sequence, see print out for reference
    vlines = []
    vlineColours = []
    timeRange = (startImageTiming, timeZ)
    lowerVlines = [24, ]
    allLevels = [k for k in list(list(sampleInfo.values())[0].keys()) if k not in ['measure', 'colour']]
    level = allLevels[0]  # use the first one

    #colours = [sampleInfo[s]['colour'].strip() for s in sampleInfo]

    # copy this script to outputPath for later references
    isSatisified = 'n'
    fig, plotData = (None, None)
    while isSatisified != 'y':
        fig, plotData = plotMeasured(allPicsData, sampleInfo, level, forceNoFillBetween,
                                     vlines=vlines, vlineColours=vlineColours, lowerVlines=lowerVlines, timeRange=timeRange)
        isSatisified = input("Satisfied with the result? y/n:")
        if isSatisified == 'y':
            break

        # Get values for the next plot
        newVlines = input("Vertical lines? Separate using spaces eg. '24 46 70'\n")
        try:
            newVlines = [int(i) for i in newVlines.split()]
            if len(newVlines) != 0:
                newVlineColours = input("Colours? Separate using spaces eg. 'k r b'\n")
                newVlineColours = [c.strip() for c in newVlineColours.split()]
                assert len(newVlineColours) == len(newVlines)
                vlines = newVlines
                vlineColours = newVlineColours
            newLowerVlines = input("Vertical lines that will plot at bottom? eg. '24 46'\n")
            try:
                newLowerVlines = [int(i) for i in newLowerVlines.split()]
                assert len(newLowerVlines) >= 1
                lowerVlines = newLowerVlines
            except:
                print(f'Lower vertical lines setup failed, use existing {lowerVlines}')
        except:
            print(f'Vertical line drawing setup failed, use existing {vlines}')
        newTimeRange = input("Time range? Separate using spaces eg. '0 72'\n")
        try:
            newTimeRange = [float(i) for i in newTimeRange.split()]
            assert len(newTimeRange) == 2 and newTimeRange[1] > newTimeRange[0]
            timeRange = newTimeRange
        except:
            print(f'Time range setup failed, use existing {timeRange}')
        newLevel = input(f"New level? {allLevels}\n")
        try:
            newLevel = newLevel.strip()
            assert newLevel in allLevels
            level = newLevel
        except:
            print(f'Level setup failed, use existing {level}')

    ################# PLOTTING DONE #########################################################

    ################# Save figure and log #########################################################
    resultDir = os.path.join(rootPath, f'result_{datetime.now().strftime("%Y.%m.%d-%H.%M.%S")}')
    os.mkdir(resultDir)
    plotData.to_csv(os.path.join(resultDir, 'plotData.tsv'), sep='\t')
    plotData.to_excel(os.path.join(resultDir, 'plotData.xlsx'))
    argumentTxt = os.path.join(resultDir, 'arguments.txt')
    fig.savefig(os.path.join(resultDir, 'figure.svg'))
    with open(argumentTxt, 'w') as f:
        f.write('python3 ' + ' '.join(sys.argv) + '\n\n')
        f.write(str(args))
        f.write(f'\n{" ".join([str(i) for i in vlines])}\t# Vertical lines')
        f.write(f'\n{" ".join(vlineColours)}\t# Vertical line colours')
        f.write(f'\n{" ".join([str(i) for i in lowerVlines])}\t# Lower vertical lines')
        f.write(f'\n{" ".join([str(i) for i in timeRange])}\t# Time range')
        f.write(f'\n{level}\t# Level')
    pathThisScript = os.path.realpath(__file__)
    for f in diffPosFiles:
        copy2(f, resultDir)
    pathFuncs = os.path.join(os.path.split(pathThisScript)[0], 'funcs')
    destFuncs = os.path.join(resultDir, 'funcs')
    try:
        copy2(pathThisScript, resultDir)
    except FileNotFoundError:
        print(f'Plain python script file {pathThisScript} not found.')
    try:
        copytree(pathFuncs, destFuncs)
    except FileNotFoundError:
        print(f'Sub-modules folder {pathFuncs} not found.')
    print('Result saved.')
