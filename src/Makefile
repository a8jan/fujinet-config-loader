# 
# FujiNet Config Loader Makefile - stripped down version of MyPicoDos Makefile
#
# MyPicoDos Makefile (c) 2003-2017 by Matthias Reichl <hias@horus.com>
# 2021 apc.atari@gmail.com - modified for FujiNet Config Loader
#

ATASM ?= ../tools/atasm/atasm

PROGS = zx0boot.bin cloader.zx0 config.com

#CASPROGS = zx0casboot.bin cascloader.zx0 config.zx0
CASPROGS = config.cas

ASMFLAGS= -Ihisio

# HISIO routines
HISIOINC = hisio/hisio.inc hisio/hisiocode.src hisio/hisiodet.src \
        hisio/hisiocode-break.src hisio/hisiocode-cleanup.src \
        hisio/hisiocode-main.src hisio/hisiocode-send.src \
        hisio/hisiocode-check.src hisio/hisiocode-diag.src \
        hisio/hisiocode-receive.src hisio/hisiocode-vbi.src


.PHONY: all cas clean zx0unpack

all: $(PROGS)

cas: $(CASPROGS)

clean:
	rm -f *.obj *.bin *.lst *.zx0
	rm -f $(PROGS) $(CASPROGS)

# ZX0 capable boot loader, 3 sectors
zx0boot.bin: zx0boot.src dzx0.src
	@echo "Building boot loader"
	$(ATASM) $(ASMFLAGS) -r -gzx0boot.lst -o$@ $<

# ZX0 capable boot loader, cassette version, 3 blocks
zx0casboot.bin: zx0boot.src dzx0.src
	@echo "Building cassete boot loader"
	$(ATASM) $(ASMFLAGS) -r -dCASSETTE=1 -gzx0casboot.lst -o$@ $<

# config loader low part - contains HISIO routines and INIT to activate them
cloader-lo.obj: cloader-lo.src cloader-hi.src zx0boot.src dzx0.src $(HISIOINC)
	@echo "Building config loader - low part"
	$(ATASM) $(ASMFLAGS) -dHIGHSPEED=1 -gcloader-lo.lst -o$@ $<

# config loader high part - config loader, display list, progress bar, banner
cloader-hi.obj: cloader-hi.src cloader-lo.src zx0boot.src dzx0.src $(HISIOINC)
	@echo "Building config loader - high part"
	$(ATASM) $(ASMFLAGS) -dHIGHSPEED=1 -dPARTHI=1 -gcloader-hi.lst -o$@ $<

# config cassette loader low part - contains INIT to activate
cascloader-lo.obj: cloader-lo.src cloader-hi.src zx0boot.src dzx0.src
	@echo "Building cassette config loader - low part"
	$(ATASM) $(ASMFLAGS) -dCASSETTE=1 -gcascloader-lo.lst -o$@ $<

# config cassette loader high part - config loader, display list, progress bar, banner
cascloader-hi.obj: cloader-hi.src cloader-lo.src zx0boot.src dzx0.src
	@echo "Building cassette config loader - high part"
	$(ATASM) $(ASMFLAGS) -dCASSETTE=1 -dPARTHI=1 -gcascloader-hi.lst -o$@ $<

# join low and high parts into one file
cloader.obj: cloader-lo.obj cloader-hi.obj
	cat cloader-lo.obj cloader-hi.obj > $@

# join low and high parts into one file
cascloader.obj: cascloader-lo.obj cascloader-hi.obj
	cat cascloader-lo.obj cascloader-hi.obj > $@

# ZX0 compressed version of config loader
cloader.zx0: cloader.obj
	@echo "Building config loader - ZX0 compressed"
	../tools/a8pack.py -c -f -v cloader.obj cloader.zx0

# ZX0 compressed version of config cassette loader
cascloader.zx0: cascloader.obj
	@echo "Building config cassette loader - ZX0 compressed"
	../tools/a8pack.py -c -f -v cascloader.obj cascloader.zx0

# relocatable ZX0 decompressor
zx0unpack: ../tools/pack/a8/zx0unpack.obj

../tools/pack/a8/zx0unpack.obj: zx0unpack-1000.obj zx0unpack-1201.obj
	@echo "Building relocatable ZX0 decompressor"
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
config.com: ../../fujinet-config/config.com
	@echo "Building compressed CONFIG"
	../tools/a8pack.py -d -v $< config.com

# compressed CONFIG, Loader compatible, DOS incompatible (no problem for cassette, bit smaller)
config.zx0: ../../fujinet-config/config.com
	@echo "Building compressed CONFIG"
	../tools/a8pack.py -c -v $< config.zx0

# combine cassette config loader with config program into single file to be loaded
casconfig.zx0: cascloader.zx0 config.zx0
	@echo "Concatenate Loader and CONFIG"
	cat cascloader.zx0 config.zx0 > casconfig.zx0

# build final bootable CAS file: zx0 cassette boot loader + program to be loaded
config.cas: zx0casboot.bin casconfig.zx0
	@echo "Building CONFIG cassette image"
	xex2cas -plain -s -r zx0casboot.bin config.cas
	xex2cas -plain -s -a casconfig.zx0 config.cas

# TODO update config.cas:
# - delete fourth (FE/zero) block
# - delete following redundant FUJI and baud sections
# - reduce IRG of next data block (from 14s to 0.25s)
# - update progress bar speed factor if necessary
# for now use hex editor ;-)
