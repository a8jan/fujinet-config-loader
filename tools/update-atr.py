#!/usr/bin/env python3

#
# update-atr.py - to update CLOADER file with size and start sector of CONFIG
#
#  2021 apc.atari@gmail.com
#


import sys
import struct


def atari_filename(fname):
    s = fname.split('.')
    name = s[0][0:8]
    if len(name) < 8:
        name += ' ' * (8-len(name))
    if len(s) > 1:
        ext = s[1][0:3]
        if len(ext) < 3:
            ext += ' ' * (3-len(ext))
    else:
        ext = '   '
    return (name+ext).upper().encode("ASCII")


def _sector_offset(sector, bps):
    if sector == 1:
        offset = 16
    elif sector == 2:
        if bps == 512:
            offset = 528
        else:
            offset = 144
    elif sector == 3:
        if bps == 512:
            offset = 1040
        else:
            offset = 272
    else:
        if bps == 512:
            offset = sector * 512 + 16
        elif bps == 256:
            offset = ((sector - 3) * 256) + 16 + 128
        else:
            offset = ((sector - 1) * 128) + 16
    return offset


def get_dentry(atr, fname, bps=128):
    a8fname = atari_filename(fname)
    for sec in range(361, 369):
        for di in range(8):
            dentry_offset = _sector_offset(sec, bps) + 16*di
            dentry = atr[dentry_offset:dentry_offset+16]
            flag = dentry[0]
            if flag == 0:
                return None
            if flag & 0x80:
                continue
            # count, ssn = struct.unpack('<HH', dentry[1:5])
            dentry_fname = dentry[5:]
            # print(f"{flag:02X} {count:04X} {ssn:04X}", dentry_fname)
            if a8fname == dentry_fname:
                dentry = atr[dentry_offset:dentry_offset+16]
                return dentry
    return None


def main():
    if len(sys.argv) != 4:
        print("Usage: update-atr.py atr_file loader_file loaded_file")
        sys.exit(1)

    atrfn = sys.argv[1]
    loaderfn = sys.argv[2]
    loadedfn = sys.argv[3]

    try:
        with open(atrfn, 'rb') as atrf:
            atr = bytearray(atrf.read())
    except Exception as e:
        print(f'Failed to read "{atrfn}"')
        print(e)
        sys.exit(-1)

    magic = struct.unpack('<H', atr[0:2])[0]
    if magic != 0x0296:
        print("ATR header missing 'NICKATARI'")
        sys.exit(-1)
    bps = struct.unpack('<H', atr[4:6])[0]

    loader_dentry = get_dentry(atr, loaderfn, bps)
    if loader_dentry is None:
        print(f'Cannot find "{loaderfn}" in "{atrfn}"')
        sys.exit(-1)
    
    loaded_dentry = get_dentry(atr, loadedfn, bps)
    if loaded_dentry is None:
        print(f'Cannot find "{loadedfn}" in "{atrfn}"')
        sys.exit(-1)
    
    count, loader_ssn = struct.unpack('<HH', loader_dentry[1:5])
    print(f'Found "{loader_dentry[5:].decode("utf-8")}" {count} sectors, starting at sector {loader_ssn}')
    if loader_ssn != 4:
        print("To get the file booted by ZX0 boot loader the start sector should be 4!")

    count, loaded_ssn = struct.unpack('<HH', loaded_dentry[1:5])
    print(f'Found "{loaded_dentry[5:].decode("utf-8")}" {count} sectors, starting at sector {loaded_ssn}')

    pbsf = 49 * 256 // (count - 2)
    if pbsf > 255:
        print("Progress bar speed factor overflow. Loaded file is too small.")
        pbsf = 255

    print("Updating ATR ...")

    offset = 16 + 128*(loader_ssn-1) + 6
    atr[offset:offset+3] = loaded_ssn & 0xFF, loaded_ssn >> 8, pbsf

    try:
        with open(atrfn, 'wb') as atrf:
            atrf.write(atr)
    except Exception as e:
        print(f'Failed to write "{atrfn}"')
        print(e)
        sys.exit(-1)

    print("Done.")


if __name__ == '__main__':
    main()
