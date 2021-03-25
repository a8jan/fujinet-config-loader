# 
# FujiNet Config Loader Makefile
#
# 2021 apc.atari@gmail.com
#

all:
	make -C src all

clean:
	make -C src clean
	rm -rf dist

dist: all
	mkdir -p dist
	cp src/*.bin dist

# To update progress bar speed factor to correspond with the size of config.com:
# (a) modify CFGSIZE in cloader.src and recompile
#     OR
# (b) run sh cloader-updater.sh cloader.bin config.com
