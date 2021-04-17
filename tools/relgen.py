#!/usr/bin/env python3

#  relgen.py - Very limited relocator generator
#    - for page only relocation
#    - for any offset relocation only if no need to relocate high bytes of word
#
#  2021 apc.atari@gmail.com
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

#
#                              ! Warning !
#
# This reloactor generator is not suitable if standalone high byte is referenced.
#
# Code like this might not work after relocation:
# LABEL   .BYTE 0
#         ...
#         LDA #>LABEL                   ; should be detected and reported
#         ...
#         .BYTE <(LABEL-1), >(LABEL)    ; will not be detected
#                                       ; it looks like world relocation
#
# a) to reloacate properly high byte, low byte must be known too to relocator
#    note: the relocation offset must be added to full LoHi word to get correct Hi byte
#    because high byte can be affected by carry when adding low bytes
#    3 or 4 builds with different offsets (and macros for high byte) would be needed
#    to build a relocation table
#
# b) relocate only by full pages (only high byte can change, not affected by low bytes)
#

import sys
import struct
import subprocess
import os


REL_WORD = 0x80
REL_HIGH = 0x40
REL_LOW  = 0x20


def add_relocation_entry(reltab, offset, type, param=None):
    # output relocation offset, relocation type and add optional param
    # s = ""
    while offset > 254:
        reltab.append(0xff)
        # s += "FF "
        offset -= 254
    reltab.append(offset)
    reltab.append(type)
    # s += f"{offset:02X} {type:02X}"
    if param is not None:
        reltab.append(param)
        # s += f" {param:02X}"
    # print(s)



def gen_relocation(fout, start1, offset, data1, data2, rel_header=True):
    i = 0
    rel = -1
    reltab = bytearray()
    while i < len(data1):
        b1 = data1[i]
        b2 = data2[i]
        if i+1 < len(data1):
            # test for relocated word
            w1 = struct.unpack('<H', data1[i:i+2])[0]
            w2 = struct.unpack('<H', data2[i:i+2])[0]
            if b1 != b2 and data1[i+1] != data2[i+1] and w1+offset == w2:
                # relocated word
                # add etry to relocation table and update relocation pointer
                add_relocation_entry(reltab, i - rel, REL_WORD)
                rel = i

                i += 2
                continue
        if b1 != b2:
            # relocated byte
            if (b1 + offset) & 0xff == b2 & 0xff:
                # low byte
                # add etry to relocation table and update relocation pointer
                add_relocation_entry(reltab, i - rel, REL_LOW)
                rel = i
            else:
                # high byte
                if offset & 0xff != 0:
                    print(f"{i-6:04X} High byte relocation detected. Relocator might not work!")
                # add etry to relocation table and update relocation pointer
                add_relocation_entry(reltab, i - rel, REL_HIGH, 0) # we don't know low byte
                rel = i
        i += 1
    # terminate relocation table - 0 (offset to next relocation)
    reltab.append(0)
    
    # print(f"relocation table ({len(reltab)}):", " ".join([f"{r:02X}" for r in reltab]))
    print(f"relocation table: {len(reltab)} bytes")

    return reltab


def main():
    if len(sys.argv) != 4:
        print("Use: relgen.py input_file1 input_file2 output_file")
        sys.exit(1)

    fn1 = sys.argv[1]
    fn2 = sys.argv[2]
    fnout = sys.argv[3]

    with open(fn1, 'rb') as f1:
        d1 = f1.read()
    with open(fn2, 'rb') as f2:
        d2 = f2.read()

    if len(d1) != len (d2):
        print("Files differs in size!")
        sys.exit(-1)

    i = 0
    offset = 0
    rel_start_next = 0x2000
    with open(fnout, 'wb') as fout:
        signature = struct.unpack('<H', d1[0:2])[0]
        if signature == 0xFFFF:
            i += 2
            fout.write(b"\xFF\xFF")
        while i < len(d1):
            if i+4 < len(d1):
                start1, end1 = struct.unpack('<HH', d1[i:i+4])
                start2, end2 = struct.unpack('<HH', d2[i:i+4])
                i += 4
                ssize = 1 + end1 - start1
                if ssize != 1 + end2 - start2:
                    print("Segments differs in size!")
                    break
                print(f"range1: {start1:04X}-{end1:04X}")
                print(f"range2: {start2:04X}-{end2:04X}")
                hdr_offset = start2 - start1
                if hdr_offset == 0:
                    print(f"using previous offset: {offset:04X}")
                else:
                    offset = hdr_offset
                    print(f"offset: {offset:04X}")
                if offset & 0xff00 == 0 or (offset & 0xff00) >> 8 == offset & 0xff:
                    print("Bad offset")
                    i += ssize
                    continue
                if offset & 0xff == 0:
                    print("Page only offset - use for page relocations.")
                if i + ssize > len(d1):
                    print("Unexpeted end of file.")
                    break
                data1 = d1[i:i+ssize]
                data2 = d2[i:i+ssize]
                reltab = gen_relocation(fout, start1, offset, data1, data2, hdr_offset!=0)
                i += ssize
            else:
                print("Unexpeted end of file.")
                break
            
            # segment header
            fout.write(struct.pack('<H', start1))
            fout.write(struct.pack('<H', start1 + ssize - 1))
            # original data
            fout.write(data1)

            # segment header
            fout.write(struct.pack('<H', 0x2DF))
            fout.write(struct.pack('<H', 0x2DF))
            # relocation hint byte (2)
            fout.write(b'\x02')

            # segment header
            if hdr_offset == 0:
                rel_start = rel_start_next
                rel_start_next += len(reltab)
            else:
                rel_start = start1 + ssize
                rel_start_next = rel_start + len(reltab)
            fout.write(struct.pack('<H', rel_start))
            fout.write(struct.pack('<H', rel_start + len(reltab) - 1))
            # relocation table
            fout.write(reltab)
            rel_start += len(reltab)

if __name__ == '__main__':
    main()
