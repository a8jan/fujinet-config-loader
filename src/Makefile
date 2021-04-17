# 
# FujiNet Config Loader Makefile - stripped down version of MyPicoDos Makefile
#
# MyPicoDos Makefile (c) 2003-2017 by Matthias Reichl <hias@horus.com>
# 2021 apc.atari@gmail.com - modified for FujiNet Config Loader
#

ATASM ?= atasm

PROGS = zx0boot.bin cloader.zx0 config.xex

all: $(PROGS)

# # version string for naming atarisio include files
# CFILE_VERSION=406

#all: MYPDOS.COM mypdos.atr mypdoshs.atr myinit2.atr

ASMFLAGS= -Ihisio
#ASMFLAGS= -Ihisio -v
#ASMFLAGS = -Ihisio -s
#ASMFLAGS = -Ihisio -v -s
#ASMFLAGS = -Ihisio -s -dHWDEBUG

# HISIO routines
HISIOINC = hisio/hisio.inc hisio/hisiocode.src hisio/hisiodet.src \
        hisio/hisiocode-break.src hisio/hisiocode-cleanup.src \
        hisio/hisiocode-main.src hisio/hisiocode-send.src \
        hisio/hisiocode-check.src hisio/hisiocode-diag.src \
        hisio/hisiocode-receive.src hisio/hisiocode-vbi.src

# # picoboot mini COM loader
# PICOBOOTSRC = picobootcode.src common.inc rreadcode.src comloadcode.src

# picoboot.bin: $(PICOBOOTSRC)
# 	$(ATASM) $(ASMFLAGS) -r -o$@ $<

# # config loader with HSIO routines included
# cloader.bin: cloader.src $(PICOBOOTSRC) $(HISIOINC)
# 	$(ATASM) $(ASMFLAGS) -dHIGHSPEED=1 -gcloader.lst -o$@ $<

# # config loader without HSIO
# cloader-nohs.bin: cloader.src $(PICOBOOTSRC) $(HISIOINC)
# 	$(ATASM) $(ASMFLAGS) -gcloader-nohs.lst -o$@ $<

# ZX0 capable boot loader, 3 sectors
zx0boot.bin: zx0boot.src dzx0.src
	$(ATASM) $(ASMFLAGS) -r -gzx0boot.lst -o$@ $<

# config loader low part - contains HSIO routines and INIT to activate them
cloader-lo.obj: cloader-lo.src cloader-hi.src zx0boot.src dzx0.src $(HISIOINC)
	$(ATASM) $(ASMFLAGS) -dHIGHSPEED=1 -gcloader-lo.lst -o$@ $<

# config loader high part - config loader, display list, progress bar, banner
cloader-hi.obj: cloader-hi.src cloader-lo.src zx0boot.src dzx0.src $(HISIOINC)
	$(ATASM) $(ASMFLAGS) -dHIGHSPEED=1 -dPARTHI=1 -gcloader-hi.lst -o$@ $<

# join low and high parts into one file
cloader.bin: cloader-lo.obj cloader-hi.obj
	cat cloader-lo.obj cloader-hi.obj > $@

# ZX0 compressed version of config loader
cloader.zx0: cloader.bin
	../tools/a8pack.py -c -f -v cloader.bin cloader.zx0

# relocatable ZX0 decompressor
../tools/pack/a8/zx0unpack.obj: zx0unpack-1000.obj zx0unpack-1201.obj
	../tools/relgen.py zx0unpack-1000-f.obj zx0unpack-1201-f.obj ../tools/pack/a8/zx0unpack.obj

# decompressor build to $1000
zx0unpack-1000.obj: zx0unpack.src dzx0.src
	$(ATASM) $(ASMFLAGS) -dUNPACKER=1 -dUNPACKSTART=4096 -gzx0unpack.lst -o$@ $<
	../tools/a8pack.py -f zx0unpack-1000.obj zx0unpack-1000-f.obj

# decompressor build to $1201
zx0unpack-1201.obj: zx0unpack.src dzx0.src
	$(ATASM) $(ASMFLAGS) -dUNPACKER=1 -dUNPACKSTART=4609 -o$@ $<
	../tools/a8pack.py -f zx0unpack-1201.obj zx0unpack-1201-f.obj

# compressed CONFIG, DOS compatible self-extracting, Loader compatible w/ inline decompression
config.xex: ../../fujinet-config/config.com ../tools/pack/a8/zx0unpack.obj
	../tools/a8pack.py -d -v ../../fujinet-config/config.com config.xex

clean:
	rm -f *.obj *.bin *.lst
	rm -f ../tools/pack/a8/zx0unpack.obj
	rm -f $(PROGS)
