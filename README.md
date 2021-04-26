# FujiNet Config Loader


This is loader for [Atari FujiNet Config](https://github.com/FujiNetWIFI/fujinet-config) program. It uses high speed SIO routines and ZX0 decompression for faster config load. When loading, the banner is shown and simple progress bar is being updated.

<img src="loader.png" alt="loader" width="400"/>

The code relies on high speed SIO routines. HISIO is part of [MyPicoDos](https://www.horus.com/~hias/atari/#mypdos), a "gamedos" for the 8-bit Ataris, written by HiassofT.

Another key component used to accelerate the loading is the [ZX0](https://github.com/einar-saukas/ZX0)  compression by Einar Saukas. Decompression routine was ported to [6502](https://xxl.atari.pl/zx0-decompressor/) by Krzysztof 'XXL' Dudek.

## How it works

Without config loader, PicoBoot boot loader loads directly FujiNet's CONFIG program.

Config loader uses ZX0 capable boot loader instead of PicoBoot. ZX0 boot loader can load regular Atari COM files as well files with ZX0 compressed segments. It allows decompression of data while loading.

The config loader is loaded and started by boot loader. Then ZX0 compressed CONFIG is loaded using HISIO and ZX0 decompression routines. Read sector routines are hooked up to allow progress bar updates.

## How to compile

HISIO code comes from MyPicoDos, so ATASM is needed to compile it (ATASM was added into `tools` directory).

Prepare and build FujiNet CONFIG program as usually, inside directory `fujinet-config`, as well ensure recent FujiNet Config Tools are available in `fujinet-config-tools` directory. Directory `fujinet-config-loader` must be at the same level as previous two.

```sh
make clean && make dist
```

Note: To rebuild `tools` directory use `make cleanall` instaed of `make clean`.

If everything goes fine, there will be new ATR image called `autorun-zx0.atr`. ATR content:
```
CLOADER.ZX0     - ZX0 compressed config loader with bundled HISIO routines and banner bitmap
CONFIG.COM      - ZX0 compressed CONFIG programm in format compatible with Atari DOS
...             - all FujiNet Config Tools like FLD, FLH, NCD, NCOPY, FMALL, etc.
```
