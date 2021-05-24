from collections import OrderedDict
from itertools import cycle

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def drawVLines(ax, li, cl, lowerVlines=[24,]):
    '''draw virtical lines on the position in li
    color in list cl'''
    yl, yh = ax.get_ylim()
    yspan = yh - yl
    for i, l in enumerate(li):
        if l in lowerVlines:
            llow = 0.05
            ltop = 0.2
            tbot = yl + yspan * 0.01
            tali = 'right'
        else:
            llow = 0.8
            ltop = 0.99
            tbot = yh + yspan * 0.01
            tali = 'center'
        ax.axvline(l, color=cl[i], ymin=llow, ymax=ltop)
        ax.text(l, tbot, f'{l}h', color=cl[i],
                horizontalalignment=tali, fontsize=7)


def plotMeasured(
    allPicsData,
    sampleInfo, # ordered dict of ordered dict
    level, # which key word to use (usually 'strain')
    forceNoFillBetween=False,
    vlines=[24, 48, 96],
    vlineColours=['k', 'b', 'r'],
    lowerVlines=[24,],
    timeRange=None, # eg. (0, 96)
    defaultColours=[f'C{i}' for i in range(10)]
):

    fig, ax = plt.subplots(1, 1)

    groups = [sampleInfo[posName][level] for posName in sampleInfo]
    uniqueGroups = []

    # Discard data out of time range
    if timeRange[0] != allPicsData.index[0] or timeRange[1] != None:
        timesFilter = (timeRange[0] <= allPicsData.index) & (allPicsData.index <= timeRange[1])
        plotRawData = allPicsData.loc[timesFilter, :]
    else:
        plotRawData = allPicsData

    defaultColours = cycle(defaultColours)

    if forceNoFillBetween:
        locs = list(sampleInfo.keys())
        for i, g in enumerate(groups):
            ax.plot(plotRawData[locs[i]], label=g, c=next(defaultColours))
        plotData = plotRawData.copy()
        plotData.columns = [f'{g}_{locs[i]}' for i, g in enumerate(groups)]
    else:
        # Deduplicate group keys under this level, keep order
        groupPoses = OrderedDict()
        for g in groups:
            if g in uniqueGroups:
                continue
            uniqueGroups.append(g)
        # Generate dictionary of group name -> position names, corresponding to the allPicsData columns to use
        for g in uniqueGroups:
            groupPoses[g] = []
            for n in sampleInfo:
                if sampleInfo[n][level] == g: groupPoses[g].append(n)
        
        # Prepare colour
        colourDict = {}
        for g in groups:
            for n in sampleInfo:
                if sampleInfo[n][level] == g:
                    c = sampleInfo[n]['colour']
                    if c == '': c = next(defaultColours)
                    colourDict[g] = c
                    break

        # prepare data AND plot
        allMeans = pd.DataFrame()  # for use of output
        allSems = pd.DataFrame()  # for use of output
        for g in uniqueGroups:
            means = plotRawData[groupPoses[g]].mean(axis=1)
            sems = plotRawData[groupPoses[g]].sem(axis=1)
            allMeans[g] = means
            allSems[g] = sems
            # Plot
            ax.plot(means, label=g, c=colourDict[g])
            if not all(pd.isna(sems)):
                ax.fill_between(means.index, means + sems,
                                means - sems, alpha=0.3)
        # output
        allMeans.columns = [f'{c}_mean' for c in allMeans.columns]
        allSems.columns = [f'{c}_sem' for c in allSems.columns]
        plotData = pd.concat((allMeans, allSems), axis=1)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')
    timeSpan = plotData.index[-1] - plotData.index[0]
    xtickInter = timeSpan//8
    ax.set_xticks(np.arange(int(plotData.index[0]), int(plotData.index[-1]), xtickInter))
    ax.set_xlim([plotData.index[0] - timeSpan * 0.05, plotData.index[-1] + timeSpan * 0.05])
    drawVLines(ax, vlines, vlineColours, lowerVlines=lowerVlines)
    plt.xlabel('time (h)')
    plt.ylabel('brightness')
    plt.title('Growth pattern', y=1.04)
    plt.legend(ncol=2, fontsize=8, framealpha=0.3)
    plt.tight_layout()
    plt.show()
    return fig, plotData
