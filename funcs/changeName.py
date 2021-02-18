'''
Image names from scanner:

Aim is to change the numbering of the files for easy parsing
first image is img_000.jpg    img_001.jpg    img_002.jpg    ...
Then the file names will be easily connected with the scanned time point.
The script is also able to preserve the file creation time in a pickle file,
and able to restore all names and times with a second run of this script on
the same directory.
Why not use the timestamp stored in the file?
    Sometimes that can be lost by copying from and to different file systems.
    This is also the reason that I stored everything in a pickle and tsv file.

After renaming the files, put files in `original_images` folder
'''


import os
import re
import pickle
#import platform
from datetime import datetime

def determineExtension(path):
    """Find the most representative file extension in this dir

    Args:
        path (str): Path to dir with images

    Returns:
        extension: ".***"
    """
    recognizableImageExtensions = ['.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.png']
    extList = []
    for file in os.listdir(path):
        _, ext = os.path.splitext(file)
        extList.append(ext)

    allExts = list(set(extList))
    mostExts = []
    occurrences = []
    for ext in allExts:
        occurrences.append(extList.count(ext))
    maxOcc = max(occurrences)
    for i, occ in enumerate(occurrences):
        if occ == maxOcc:
            mostExts.append(allExts[i])
    while len(mostExts) != 1:
        # remove none image extensions
        remove = False
        for ext in mostExts:
            if ext not in recognizableImageExtensions:
                mostExts.remove(ext)
                remove = True
        if len(mostExts) == 0:
            print(f"I didn't recognise any image files in this path.\n{path}")
            return None, None
        if not remove:  # means there are two image format with equal amount, ask for help
            isSet = False
            while not isSet:
                ext = input(
                    f"I find multiple extensions in {path},\nplease choose one:\n{mostExts}\n")
                if ext in mostExts:
                    mostExts = [ext, ]
                    isSet = True
                else:
                    print('Please type in ".***" (including the dot)')
    extension = mostExts[0]
    return extension
# determineExtension()


def determinePrefixExtension(path):
    """Find extension first, by the most aboundant and picture ones,
    Find prefix second, by remove numbering of files with found extension.

    Args:
        path (str): Path to dir with images

    Returns:
        prefix, extension, totalNum, digits: 
            prefix - file name prefix
            extension - extension of these files
            totalNum - number of files with the prefix and extension
            digits - number of digits of the numbering needed (for downstream zfill)
    """
    filesFolders = os.listdir(path)
    if 'original_images' in filesFolders:
        path = os.path.join(path, 'original_images')
        filesFolders = os.listdir(path)
    extension = determineExtension(path)
    # find prefix
    prefixList = []
    totalNum = 0
    for file in filesFolders:
        name, ext = os.path.splitext(file)
        if ext == extension:
            totalNum += 1
            nums = re.findall(r'[0-9]+', name)
            if len(nums) != 0:
                num = nums[-1]
                prefix = name[:-len(num)]
            else:
                continue
            prefixList.append(prefix)
    # dereplication
    prefixList = list(set(prefixList))
    while len(prefixList) != 1:  # ask for help
        isSet = False
        while not isSet:
            prefix = input(
                f"I don't know which prefix is correct, please choose one:\n{prefixList}\n")
            if prefix in prefixList:
                prefixList = [prefix, ]
                isSet = True
            else:
                print('Please type in any of the above.')
    prefix = prefixList[0]

    if totalNum < 100:
        digits = 2
    elif totalNum < 10000:
        digits = 3
    elif totalNum < 100000:
        digits = 4
    else:
        print(f'Are you sure, {totalNum} of files? (I quit)')
        exit()

    return prefix, extension, totalNum, digits
# determinePrefixExtension


def getScanTime(filePath):
    """Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.

    Args:
        filePath (str): path to file

    Returns:
        timeCreation: 
            os.path.getctime(filePath)
    """
    #if platform.system() == 'Windows':
    #    timeCreation = os.path.getctime(filePath)
    #else:
    timeCreation = os.stat(filePath).st_mtime
    return timeCreation
# getScanTime


def genLogFile(path):
    return os.path.join(path, 'nameTimeLog')


def changeToNew(path, dictOld2New, dictOldScanTime):
    """Parse all file names, make file names easier to parse in the following steps.
    Pass {} for dictOld2New and {} for dictOldScanTime if fresh.
    After rename, moveToOriDir() will be called, all file will be moved to a folder called
    'original_images' in this path

    Args:
        path (str): path to dir
        dictOld2New (dict): {'old': 'new'}
        dictOldScanTime (dict): {'old': timestamp}

    Raises:
        NameError: If more than one file is found with no numbering
    """
    logFile = genLogFile(path)
    isFresh = False
    # if empty dict is passed, then I know file names are intact
    prefix, extension, totalNum, digits = determinePrefixExtension(path)
    if len(dictOld2New) == 0:
        isFresh = True
        files = [file for file in os.listdir(path) if file.endswith(extension)]
    else:
        files = dictOld2New.keys()

    # Collect info, prepare old and new names in a dict
    nameChangeDict = {}  # {'old': 'new'}
    for oldName in files:
        oldFilePath = os.path.join(path, oldName)
        if isFresh:
            foundNo1 = False
            nums = re.findall(r'[0-9]+', oldName)
            if len(nums) != 0:
                num = int(nums[-1]) - 1  # scanner starts numbering from 2
            else:
                num = 0
                if foundNo1:
                    raise NameError('Another file with no numbering?')
                else:
                    foundNo1 = True
            if not oldName.startswith(prefix[:-1]):
                print(f'{oldName} not starts with {prefix}')
                continue
            newName = f'{prefix}{str(num).zfill(digits)}{extension}'
            dictOld2New[oldName] = newName
            dictOldScanTime[newName] = getScanTime(oldFilePath)
        else:
            newName = dictOld2New[oldName]
        newFilePath = os.path.join(path, newName)
        if os.path.isfile(newFilePath):
            newFilePath = f"{newFilePath}_temp"
        nameChangeDict[oldFilePath] = newFilePath

    # If preparation finished with no error, do change name
    for oldFilePath in nameChangeDict:
        newFilePath = nameChangeDict[oldFilePath]
        os.rename(oldFilePath, newFilePath)
    for file in os.listdir(path):
        if file.endswith('_temp'):
            name = file[:-5]
            tempPath = os.path.join(path, file)
            correctPath = os.path.join(path, name)
            os.rename(tempPath, correctPath)
    isNew = True

    # write info to new file
    with open(logFile, 'wb') as fileNameLog:
        pickle.dump((dictOld2New, dictOldScanTime, isNew), fileNameLog)

    # Move file:
    moveToOriDir(path, logFile)
# changeToNew


def changeToOld(path, dictOld2New, dictOldScanTime):
    """Will first move all files from 'original_images' dir out and then
    change file names to the original stats based on info in dictOld2New.
    The file creation (modification) time will not be altered.

    Args:
        path (str): path to dir
        dictOld2New (dict): {'old': 'new'}
        dictOldScanTime (dict): {'old': timestamp}
    """
    logFile = genLogFile(path)
    # move file back
    moveToOriDir(path, logFile, back=True)

    nameChangeDict = {}
    for oldName in dictOld2New:
        oldFilePath = os.path.join(path, oldName)
        newName = dictOld2New[oldName]
        newFilePath = os.path.join(path, newName)
        if not os.path.isfile(newFilePath):
            raise NameError(f'File not found {newFilePath}')
        if os.path.isfile(oldFilePath) and newFilePath != oldFilePath:
            # the original file name is being occupied by a different file
            oldFilePath = f'{oldFilePath}_temp'
        atime = dictOldScanTime[newName]
        mtime = dictOldScanTime[newName]
        nameChangeDict[oldFilePath] = (newFilePath, atime, mtime)
    for oldFilePath in nameChangeDict:
        newFilePath, atime, mtime = nameChangeDict[oldFilePath]
        os.rename(newFilePath, oldFilePath)
        os.utime(oldFilePath, (atime, mtime))
    # Deal with temp file names
    for file in os.listdir(path):
        if file.endswith('_temp'):
            name = file[:-5]
            tempPath = os.path.join(path, file)
            correctPath = os.path.join(path, name)
            os.rename(tempPath, correctPath)
    isNew = False
    # refresh info file
    with open(logFile, 'wb') as fileNameLog:
        pickle.dump((dictOld2New, dictOldScanTime, isNew), fileNameLog)
# changeToOld


def changeFileName(path, reverse=True):
    """Wraper changeToNew() and changeToOld()

    Args:
        path (str): path of the dirctory

    Returns:
        logFile: Path to the log file in the dirctory,
                 Binary pickle containing (dictOld2New, dictOldScanTime, isNew)
    """
    logFile = genLogFile(path)

    if os.path.isfile(logFile):
        with open(logFile, 'rb') as f:
            dictOld2New, dictOldScanTime, isNew = pickle.load(f)
        if isNew and reverse:
            changeToOld(path, dictOld2New, dictOldScanTime)
        else:  # then we need to change back
            changeToNew(path, dictOld2New, dictOldScanTime)
    else:
        dictOld2New = {}
        dictOldScanTime = {}
        changeToNew(path, dictOld2New, dictOldScanTime)
    writeTable(path, logFile)
# changeFileName()


def moveToOriDir(path, logFile, back=False):
    with open(logFile, 'rb') as fileNameLog:
        dictOld2New, _, _ = pickle.load(fileNameLog)
    tDir = os.path.join(path, 'original_images')
    if not os.path.isdir(tDir):
        os.mkdir(tDir)
    for oldName in dictOld2New:
        newName = dictOld2New[oldName]
        newFileOriPath = os.path.join(path, newName)
        newFileTarPath = os.path.join(tDir, newName)
        if back:
            os.rename(newFileTarPath, newFileOriPath)
            pass
        else:
            os.rename(newFileOriPath, newFileTarPath)
    if back:
        try:
            os.rmdir(tDir)
        except:
            pass
# moveToOriDir()


def writeTable(path, logFile):
    """
    TSV file is written separately
    path can be a different directory
    logFile is the full path to the logFile

    Args:
        path (str): path to the directory
        logFile (str): path of log file generated by changeFileName(path),
                       This file is binary pickle containing (dictOld2New, dictOldScanTime, isNew)
    """
    with open(logFile, 'rb') as fileNameLog:
        dictOld2New, dictOldScanTime, _ = pickle.load(fileNameLog)
    for newName in dictOldScanTime:
        timeCreation = dictOldScanTime[newName]
    maxTime = max(dictOldScanTime.values())
    minTime = min(dictOldScanTime.values())
    maxDate = datetime.fromtimestamp(
        maxTime).strftime("%A, %d %B %Y, %H:%M:%S").split(', ')[1]
    minDate = datetime.fromtimestamp(
        minTime).strftime("%A, %d %B %Y, %H:%M:%S").split(', ')[1]
    logTsv = os.path.join(path, f'scanLog{minDate}-{maxDate}.tsv'.replace(' ', '_'))

    if os.path.isfile(logTsv):
        pass
    else:
        with open(logTsv, 'w') as logTsv:
            lines = []
            for oldName in dictOld2New:
                newName = dictOld2New[oldName]
                timeCreation = dictOldScanTime[newName]
                timeStr = datetime.fromtimestamp(
                    timeCreation).strftime("%A, %d %B %Y, %H:%M:%S")
                weekDay = timeStr.split(', ')[0]
                scanDate = timeStr.split(', ')[1]
                scanTime = timeStr.split(', ')[2]
                lines.append(
                    f'{oldName}\t{newName}\t{weekDay}\t{scanDate}\t{scanTime}\n')
            lines.sort(key=lambda line: line.split('\t')[1])
            lines.insert(0, 'old_name\tnew_name\tweek_day\tdate\tscan_time\n')
            logTsv.writelines(lines)
# writeTable()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='pass a directory as first argument')
    parser.add_argument('path')
    args = parser.parse_args()
    path = args.path

    changeFileName(path)
