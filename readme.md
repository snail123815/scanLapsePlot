# scanLapsePlot

From time lapse pictures to a plot that you need!

## Example output:

### Single lined

<img src=https://raw.githubusercontent.com/snail123815/scanLapsePlot/main/example_results/single_lined/figure.svg>

### With sem

<img src=https://raw.githubusercontent.com/snail123815/scanLapsePlot/main/example_results/with_sem/figure.svg>

## Usage

[work in progress]

### Help information

This is a command line program, before using, check the command line help info:

```powershell
PS C:\Users\user> .\Downloads\scanLapsePlot_v1.0-beta_Windows\extractPicAndMeasure.exe -h
```

or in macOS Big Sur (M1 not tested)

```shell
user@your-Mac ~ % Downloads/scanLapsePlot_v1.0-beta_MacOS_BigSur/extractPicAndMeasure -h
```

or run the source code script directly if you have python3.9 or above and have required packages installed.

```shell
user@your-Mac ~ % python3.9 Downloads/scanLapsePlot/extractPicAndMeasure.py -h
```

Help information:

```raw
usage: extractPicAndMeasure.py [-h] [--normType {None,Each,Combined}] [--endTiming ENDTIMING]
                               [--percentage PERCENTAGE] [-r FLOAT] [--noTimeFromFile]
                               [--locationFromCropped] [--forceNoFillBetween]
                               [--imageInterval IMAGEINTERVAL]
                               [--startImageTiming STARTIMAGETIMING] [--reExtract]
                               [--reMeasure] [--diffPos [DIFFPOS ...]]
                               rootPath sampleInfoTsvPath

positional arguments:
  rootPath              Path to process, with original_images dir
  sampleInfoTsvPath     tsv file for sample information, same name will be averaged, when
                        multiple location files are needed, use the first one for this
                        mandatory argument

optional arguments:
  -h, --help            show this help message and exit
  --normType {None,Each,Combined}
                        Specify how the normalisation is done
  --endTiming ENDTIMING
                        The time of the last picture to plot, in hours
  --percentage PERCENTAGE
                        This precent is to specify the precentage of the picture width to be
                        considered
  -r FLOAT, --resizeFactor FLOAT
                        Factor of original size (0-1), default 0.35
  --noTimeFromFile      Time from original file will be stored in all new files if this is
                        not set
  --locationFromCropped
                        Set if the locations are measured from images in "cropped_ori"
                        folder. Will only take effect if "original_images" folder is gone.
  --forceNoFillBetween  fill between stderr if not set
  --imageInterval IMAGEINTERVAL
                        Hours, only affect if --noTimeFromFile is set or the creation time
                        cannot be obtained from file
  --startImageTiming STARTIMAGETIMING
                        The timing of the first picture, in hours
  --reExtract           Force re-extract pictures
  --reMeasure           Force re-measure
  --diffPos [DIFFPOS ...]
                        If your plates was moved during experiment, then you need multiple
                        position files. This argument allows you to do: [start file]
                        [positionTsvPath] [start file] [positionTsvPath]... DO NOT add the
                        first file (start from 0) again. The START FILE is the file name of
                        the original file name. Check the log file for the old name.
```

### Generate information table

The easiest way is to use imageJ:

1. Set measurments  
   Analyze -> Set Measurements -> Bounding rectangle
2. Make selection and measure (obtain the location of top left corner and the size)  
3. Copy location info to the **location section** of `extractPicture_PositionsAndInfo.tsv`
4. Assign sample information to each location in the **sample info section** of `extractPicture_PositionsAndInfo.tsv`

If polygon selection is needed, please record macros while making the polygon selection:  
Plugins -> Macros -> Record  
Then copy the recorded macro string to the **location section** of `extractPicture_PositionsAndInfo.tsv`

### Process all images and make plots

In a shell environment:

```shell
> extractPicAndMeasure [-h] [--normType {None,Each,Combined}] [--endTiming ENDTIMING]
                       [--percentage PERCENTAGE] [-r FLOAT] [--noTimeFromFile]
                       [--locationFromCropped] [--forceNoFillBetween]
                       [--imageInterval IMAGEINTERVAL]
                       [--startImageTiming STARTIMAGETIMING] [--reExtract]
                       [--reMeasure] [--diffPos [DIFFPOS ...]]
                       rootPath sampleInfoTsvPath
```

After execution, a plot will show to let you preview the result. When this plot is closed, go back to the shell environment for possible modifications to the plot, including drawing vertical lines at desired location and specify the range of plotting. Once you are satisfied with the result, answer y to the question, the program will create a `result_[day]_[time]` folder in the root path and store data and figure in that folder.

### Colours

To assign any colours, please use Matplotlib colour string, refer to

https://matplotlib.org/stable/gallery/color/named_colors.html

## Running prerequisites

First you need python3.9. Lower versions not tested.

```shell
> pip3 install --user matplotlib pandas numpy pillow scikit-image openpyxl
```

## Build binary

Except running prerequisites, you need to install pyinstaller using pip:

```shell
> pip3 install pyinstaller
```

### For MacOS (compiled in Big Sur 11.2.1)

```shell
> pyinstaller -F extractPicAndMeasure.py --distpath Dist --workpath building_temp --hidden-import openpyxl --hidden-import cmath
```

(Ignore errors for the system imports, they are hidden by Big Sur. But will work fine because every Big Sur have those files.)

`cmath` was found during testing in a fresh Big Sur.

### For Windows (Windows 10 tested)

Of course you need to do the compilation on Windows.

```powershell
PS C:\Users\user> pyinstaller -F extractPicAndMeasure.py --distpath Dist --workpath building_temp --hidden-import openpyxl --hidden-import cmath
```

No special errors happened. It seems that `openpyxl` import has been recognised automatically.

## Bug

- [x] Changeing time range only eliminates the data but not resetting xrange
- [ ] Data saving do not include some data columns. Column names are full, but data lost.