#!/bin/sh

# 2021 apc.atari@gmail.com

# Updates progress bar speed factor in cloader.bin
# to correspond with the size of loaded file

# usage: sh cloader-updater.sh cloader.bin config.com

# see cloader.src for formula details
echo "Updating $1 to match size of $2"
BYTES=$(stat -c '%s' "$2")
BLOCKS=$((($BYTES + 124) / 125))
FACTOR=$((12544 / $BLOCKS))
FACTORHEX=$(/usr/bin/printf %x $FACTOR)
echo "  bytes: $BYTES  blocks: $BLOCKS  progress bar speed factor: $FACTOR (\$$FACTORHEX)"

/usr/bin/printf "\x$FACTORHEX" | dd of="$1" bs=1 seek=21 count=1 conv=notrunc
