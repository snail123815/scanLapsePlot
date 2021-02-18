import os
import shutil

def createFolders(targetPath, folders, reset=False):
    targetPaths = {}
    for folder in folders:
        newPath = os.path.join(targetPath, folder)
        try:
            os.makedirs(newPath)
        except FileExistsError:
            if reset:
                try:
                    shutil.rmtree(newPath)
                    os.mkdir(newPath)
                except FileNotFoundError:
                    pass
            pass
        targetPaths[folder] = newPath
    return targetPaths
# createFolders
