import codecs  # for possible unicode character, not fully tested
from collections import OrderedDict

import numpy as np

def getInfo(sampleInfoTsvPath):
    """Parse only the sampleInfo part of the file
					
    sampleInfo	strain	measure	colour		# measure in ['circle', 'square', 'polygon']
    1	M145_MM	circle	firebrick		# colour will be default if empty
    2	M145_MeJA	circle	lightsalmon		
    3	Δrag_MeJA	circle	lightsteelblue		
    4	Δrag_JA	circle	royalblue		
    5	Δrag_MM	circle	darkblue 		
    6	M145_JA	circle	tomato		
    END_INFO # DO NOT DELETE THIS LINE									

    Args:
        sampleInfoTsvPath (str): metadata tsv file

    Returns:
        sampleInfo: Dict: sampleInfo[posName][infoType]
    """
    sampleInfo = OrderedDict()
    with codecs.open(sampleInfoTsvPath, encoding='utf-8', mode='r') as posFile:
        infoStarted = False
        sampleInfoHeader = []
        for line in posFile.readlines():
            if line.startswith('#') or len(line) == 0 or line.startswith('"#') :
                continue
            if not infoStarted and not line.startswith('sampleInfo'): continue
            elements = [elem.strip() for elem in line.split('\t')]
            for i, e in enumerate(elements):
                if e.startswith('"') and e.endswith('"'):
                    elements[i] = e[1:-1]
            elements = [elem for elem in elements if elem != '']
            elements = [elem for elem in elements if not elem.startswith('#')]
            if len(elements) == 0: continue
            if elements[0] == 'sampleInfo':
                infoStarted = True
                sampleInfoHeader = [e for e in elements[1:]]
                continue
            if not infoStarted:
                continue
            posName = elements[0]
            if posName.startswith('END_INFO'):
                break
            sampleInfo[posName] = OrderedDict()
            for i, infoType in enumerate(sampleInfoHeader):
                try:
                    e = elements[i + 1]
                except IndexError:
                    e = None
                sampleInfo[posName][infoType] = e
    return sampleInfo


def getPositions(positionTsvPath):
    """Example position file:

    CornerSize     x      y      size           # upper left corner position
    TL             420    350    1040
    TR             1460   350    1040
    ML             90     1390   1040
    MR             1100   1390   1040
    BL             420    2400   1040
    BR             1460   2400   1040
    WidthHeight    x      y      Width  Height  # upper left and lower right positions
    removePadding  52     360    2448   3080    # include this line if you need to remove certain padding
    TwoPositions   x1     y1     x2     y2

    END_POSITION # Location parse will stop here. DO NOT DELETE THIS LINE	

    Args:
        positionTsvPath ([type]): [description]

    Returns:
        posDict: x1, y1, x2, y2 (designed for PIL.image.crop)
    """
    positionTypes = ['CornerSize', 'WidthHeight', 'CentreSize', 'TwoPositions', 'Polygon', 'removePadding']
    posDict = {}
    locType = ''
    with open(positionTsvPath, 'r') as posFile:
        for line in posFile.readlines():
            if line.startswith('#') or len(line) == 0 or line.startswith('"#') :
                continue
            elements = [e.strip() for e in line.split('\t')]
            for i, e in enumerate(elements):
                if e.startswith('"') and e.endswith('"'):
                    elements[i] = e[1:-1]
            if elements[0].startswith('END_POSITION'):
                break
            elements = [e for e in elements if e != '' and not e.startswith('#')]
            if len(elements) == 0:
                continue
            if elements[0] in positionTypes:
                # Type string found, initialise
                pLocType = locType # store previous locType in case we find 'removePadding'
                locType = elements[0]
                posDict[locType] = {}
                # remove padding deal here, only allowing 'WidthHeight' and 'TwoPositions'
                if locType == 'removePadding':
                    assert pLocType in ['TwoPositions', 'WidthHeight'], f'Please set padding position under "WidthHeight" and "TwoPositions", now it is under "{pLocType}"'
                    position = [int(elem) for elem in elements[1:]]
                    # already obey rule of "TwoPositions"
                    if pLocType == 'WidthHeight':
                        position = position[:2] + [sum(x) for x in zip(position[2:], position[:2])]
                    posDict['removePadding']['paddingPos'] = position[:4]
                continue
            # NOW start parsing positions
            if locType == '':
                raise ValueError(f'Error, no type string found, check file.\nAcceptable: {", ".join(positionTypes)}')
            posName = elements[0]
            if locType == 'Polygon': # imageJ marco: makePolygon(852,588,660,1184,1288,1216);
                polygon = (int(i) for i in elements[1][12:-2].split(','))
                polygon = np.array(polygon)
                xmax = polygon[::2].max()
                xmin = polygon[::2].min()
                ymax = polygon[1::2].max()
                ymin = polygon[1::2].min()
                posDict['Polygon_square'][posName] = (xmin, ymin, xmax, ymax)
                posDict['Polygon_poly'][posName] = polygon
            else:
                position = [int(elem) for elem in elements[1:]]
                if locType == 'CornerSize':
                    size = position[2]
                    position = position[:2] + [x + size for x in position[:2]]
                elif locType == 'CentreSize':
                    r = int(position[2] / 2)
                    position = [x - r for x in position[:2]] + [x + r for x in position[:2]]
                elif locType == 'WidthHeight':
                    position = position[:2] + [sum(x) for x in zip(position[2:], position[2:4])]
                elif locType == 'TwoPositions':
                    position = position[:4]
                posDict[locType][posName] = position
    # Put None for removePadding if not found in the file
    if 'removePadding' not in posDict:
        posDict['removePadding']['paddingPos'] = None
    return posDict
# getPositions


def getPosToCrop(posDict, useCroppedImg=False, locFromCropped=False):
    posToCrop = {}
    for posType in posDict:
        if posType in ['removePadding', 'Polygon_poly']:
            continue
        if len(posDict[posType]) == 0:
            continue
        for posName in posDict[posType]:
            position = posDict[posType][posName]
            if useCroppedImg and not locFromCropped:  # change to new coordinate
                paddingPos = posDict['removePadding']['paddingPos']
                position = [x[0]-x[1] for x in zip(position[:4], paddingPos[:2] * 2)]
            posToCrop[posName] = position
    return posToCrop