# 
# FujiNet Config Loader Makefile
#
# 2021 apc.atari@gmail.com
#

all:
	make -C src all

clean:
	make -C src clean
	rm -f autorun-zx0.atr
	rm -rf dist

dist: all
	mkdir -p dist
	cp src/cloader.zx0 dist/
	cp src/config.xex dist/
	cp ../fujinet-config-tools/dist/*.COM dist/ || true
	cp ../fujinet-config-tools/dist/*.com dist/ || true
	rm -f autorun-zx0.atr
	dir2atr -m -S -B src/zx0boot.bin autorun-zx0.atr dist/

# To update progress bar speed factor to correspond with the size of config.com:
# (a) modify CFGSIZE in cloader.src and recompile
#     OR
# (b) run sh cloader-updater.sh cloader.bin config.com
