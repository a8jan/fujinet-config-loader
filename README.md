# FujiNet Config Loader


This is loader for [Atari FujiNet Config](https://github.com/FujiNetWIFI/fujinet-config) program. It uses high speed SIO routines for faster config load. When loading, the banner is shown and simple progress bar is being updated.

The code relies on PicoBoot and high speed SIO routines. Both are part of [MyPicoDos](https://www.horus.com/~hias/atari/#mypdos), a "gamedos" for the 8-bit Ataris, written by HiassofT.

![](loader.png)

## How it works

Without config loader, PicoBoot boot loader loads directly FujiNet config. With config loader, the config loader is loaded and started first and then FujiNet config is loaded using included HSIO routines. HSIO routines are used for faster data transfers. PicoBoot routines are called to get COM file (CONFIG.COM) loaded. PicoBoot routines are hooked up to allow progress bar updates with each sector being read.

## How to compile

Most of the code comes from MyPicoDos, so ATASM is needed to compile it.

```sh
make clean && make dist
```

When everything goes fine, the `dist` directory will be populated with couple of files

- `cloader.bin` - Config Loader executable
- `cloader-nohs.bin` - smaller variant, high speed routines not included
- `cloader.dat` - banner bitmap, 256x32 pixels mono (ANTIC mode 15, narrow play field), 1KB
- `picoboot.bin` - boot sectors

## How to use it

The order of files in (Atari image) directory is important. It must be: 1) CLOADER.BIN 2) CLOADER.DAT 3) CONFIG.COM 4) all other files. This should not be a problem with current file names used by FujiNet Config and FujiNet Config Tools. Just place all necessary files into single directory and use dir2atr to create a disk image, set picoboot.bin for boot sectors.

For example to create `autorun.atr` disk image with FujiNet Config and FujiNet Config Tools included:

```sh
# assuming directories and files are prepared like this
fujinet-config/config.com
fujinet-config-loader/dist	# contains loader files
fujinet-config-tools/dist	# contains tools files

# enter config directory
cd fujinet-config

# put all necessary files into dist directory
mkdir -p dist
cp ../fujinet-config-tools/dist/*.com dist/
cp ../fujinet-config-loader/dist/cloader.bin dist/
cp ../fujinet-config-loader/dist/cloader.dat dist/
sh ../fujinet-config-loader/cloader-updater.sh dist/cloader.bin config.com
cp config.com dist/

# create new ATR disk image
rm autorun.atr
dir2atr -m -S -B ../fujinet-config-loader/dist/picoboot.bin autorun.atr dist/

```

The resulting `autorun.atr` image file can be inserted into Disk Slot 1 and booted as any regular disk image. If everything would work fine it can be included into firmware and tested as part of the firmware.

## Note about progress bar

Progress bar is 48 pixels wide bar and it should go from 0 to 48 pixels when loading config.com file into memory. Those 48 pixels needs to be aligned with the file size of program being loaded. For this purpose there is a progress bar speed factor (PBSF in cloader.src) which is used to translate read blocks to pixel updates.

Currently the PBSF is fixed value in source code and with new build of config.com the PBSF should be updated to match the new file size. This can be done in one of two ways:

a) Modify cloader.src, CFGSIZE should be updated to the new files size of config.com (bytes) and do a rebuild. PBSF value is calculated from CFGSIZE.

OR

b) The `cloader-updater.sh` script can be used to calculate new value and update the PBSF byte in existing cloader.bin file. No need to recompile the loader. This method is used in above example.

Used formulas assumes SD format with 125 data bytes per sector will be used.

Another solution is to let the loader calculate PBSF prior loading the file but this would increase the code size (which is loaded with standard/slow SIO) ... .. and I am lazy to code it now ;-)