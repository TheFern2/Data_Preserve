# Data_Preserve

## Description
This project started small.  The intent was to only save tag information from Allen Bradley PLC through Ethernet communication, but then it grew to loading and verifying. Soon after that I wanted more visual feedback so I added a progress bar, and later on an error log. The settings can be changed through an INI file without the need to recompile the exe which I did in pyinstaller, useful for machines without python.

The reason I wrote this utility was that the current tool I had at hand was too slow and progress feedback was terrible through the HMI. At times I thought the HMI froze up. This utility is useful if you want to save data and load it back on another PLC, or even the same one after an update. Useful for saving calibration data, setup data, or any data that should be loaded back in the PLC after a full download. By data I mean Allen Bradley controller tags or program tags.

## Dependencies
The main driver for this project is pylogix by Dustin Roeder. 

 -  [pylogix](https://github.com/dmroeder/pylogix) (pip in the near future, need eip.py and lgxDevice.py in the same directory as data_preserve.py)
 - ping3 (pip)
 - progress (pip)

## Settings
If you download the compiled exe, all you need to do is change the settings.
Settings are easy enough. If you want to have the config files on the root directory with data_preserve.py or data_preserve.exe leave Save_Path empty. You can also use UNC paths. \\192.168.1.13\c$\PathToFiles\

Lastly add the file names of your config files which can use any extension note that case is sensitive for file names and Files_Extension. The names to the left of the equal sign under [Files_Path] can be changed to anything too.

Settings.ini below:

[Settings]  
PLC_IP=10.0.2.15  
PLC_SLOT=2  
Save_Path=C:\\PathToFiles\\  
Files_Extension=CFG  
  
; Add data preserve files below without extension  
[Files_Path]  

File_01=My_DPreserve  
File_02=My_DPreserve_2

## Configuration Files
The configuration files can be named anything, and have any extension you'd like. I use CFG for configuration but that's an arbitrary name.

The file should include the tags you want to save. At the time of writing the utility, supports BOOL, REAL, DINT, SINT. For whatever reasons the CFG files that I initially wrote the script for contained BIT which is the same as BOOL, nevertheless stick to using BOOL.

**NameOfTag||TYPE**

```
Nums[0]||REAL
Bools[0]||BOOL
Program:MainProgram.Test_01||DINT
Program:MainProgram.Test_02||BOOL
Program:MainProgram.Test_03||REAL
Program:MainProgram.Test_04||SINT
```

**FileName_Save.CFG** [After saving]

```
Nums[0]|0.5|REAL
Bools[0]|True|BOOL
Program:MainProgram.Test_01|453|DINT
Program:MainProgram.Test_02|False|BOOL
Program:MainProgram.Test_03|2.5|REAL
Program:MainProgram.Test_04|111|SINT
```

## Launching
Launch the exe or py script and make sure the settings.ini is in the same directory and your path to the files is correct.
![enter image description here](https://i.imgur.com/UdBWh5H.png)

Save: This will save the data for all the tags in your configuration files.
Load: This will load the FileName.CFG tags to the PLC (**Will overwrite tags online: Use caution if you don't know what you're doing!**)
Verify: Verifies the tags with online, it doesn't modify any files nor online plc data.

![Imgur](https://i.imgur.com/kPFRleP.png)

Note the log.txt if there are any tags that do not exist in the PLC you'll see errors there. I've added a few erroneous tags as an example. Yeah I misspelled Unknown : )

![Imgur](https://i.imgur.com/hhxzzkY.png)

Loading: (Note that loading verifies too)
If all the tags are on the + sign they loaded correctly to the PLC, the ones on the - sign did not load or did not exist.

![Imgur](https://i.imgur.com/ECMP6bX.png)

