# Title

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

MD5: `c8e1dce1f3c8278d44c6aba28170b3e2 extractPicAndMeasure`

SHA1: `f9a462f3ec452aca18732ef0bb664a10fe8715ff extractPicAndMeasure`

### For Windows (Windows 10 tested)

Of course you need to do the compilation on Windows.

```powershell
> pyinstaller -F extractPicAndMeasure.py --distpath Dist --workpath building_temp --hidden-import openpyxl --hidden-import cmath
```

No special errors happened. It seems that `openpyxl` import has been recognised automatically.

MD5: `cc884ea5452d214801d6581e84017a27 extractPicAndMeasure.exe`

SHA1: `26af10900a256af7f2c95f6fb3a48d0dc51650fb extractPicAndMeasure.exe`