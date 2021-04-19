# 
# FujiNet Config Loader Makefile
#
# 2021 apc.atari@gmail.com
#

.PHONY: all dist tools clean cleantools cleanall

all: tools
	@echo "Building CONFIG loader"
	make -C src all

tools:
	@echo "Building tools"
	make -C tools all
	make -C src zx0unpack

clean:
	make -C src clean
	rm -f autorun-zx0.atr
	rm -rf dist

cleantools:
	make -C tools clean

cleanall: clean cleantools

dist: all
	@echo "Building ATR disk image"
	mkdir -p dist
	cp src/cloader.zx0 dist/
	cp src/config.xex dist/
	cp ../fujinet-config-tools/dist/*.COM dist/ || true
	cp ../fujinet-config-tools/dist/*.com dist/ || true
	rm -f autorun-zx0.atr
	dir2atr -m -S -B src/zx0boot.bin autorun-zx0.atr dist/
	tools/update-atr.py autorun-zx0.atr cloader.zx0 config.xex

# To update progress bar speed factor to correspond with the size of config.com:
# (a) modify CFGSIZE in cloader.src and recompile
#     OR
# (b) run sh cloader-updater.sh cloader.bin config.com
