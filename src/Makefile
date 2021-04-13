# 
# FujiNet Config Loader Makefile - stripped down version of MyPicoDos Makefile
#
# MyPicoDos Makefile (c) 2003-2017 by Matthias Reichl <hias@horus.com>
# 2021 apc.atari@gmail.com - modified for FujiNet Config Loader
#

ATASM ?= atasm

# PROGS = picoboot.bin cloader.bin cloader-nohs.bin
PROGS = zx0boot.bin cloader.bin 

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

zx0boot.bin: zx0boot.src
	$(ATASM) $(ASMFLAGS) -r -gzx0boot.lst -o$@ $<

# config loader low speed part - contains HSIO routines
cloader-lo.obj: cloader-lo.src cloader-hi.src zx0boot.src $(HISIOINC)
	$(ATASM) $(ASMFLAGS) -dHIGHSPEED=1 -gcloader-lo.lst -o$@ $<

# config loader high speed part - Config load using hybrid loader, display list, progress bar, banner
cloader-hi.obj: cloader-hi.src cloader-lo.src zx0boot.src $(HISIOINC)
	$(ATASM) $(ASMFLAGS) -dHIGHSPEED=1 -dPARTHI=1 -gcloader-hi.lst -o$@ $<

cloader.bin: cloader-lo.obj cloader-hi.obj
	cat cloader-lo.obj cloader-hi.obj > $@

clean:
	rm -f *.obj *.bin *.lst
