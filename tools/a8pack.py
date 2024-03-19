#!/usr/bin/env python3

#  a8pack.py - Packer for Atari DOS files
#    manipulates and packs segmented Atari DOS files
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


import sys
import os
import struct
import subprocess
import re

SEGMENT_SIGNATURE = 'SIGNATURE' # 0xffff
SEGMENT_DATA = 'DATA'           # standard data block with: start,end,data[1+end-start]
SEGMENT_PACKED = 'PACKED'       # compressed data: start,0x0000,packer method (1 byte),data[unknown length when saved]

PACK_LZ4 = 0x00
PACK_APL = 0x01
PACK_ZX0 = 0x02

REL_WORD = 0x80
REL_HIGH = 0x40
REL_LOW  = 0x20

# attempt to support generic packers
packers = {
    # packer ID: name, pack command template, relocatable unpacker
    PACK_ZX0: ("ZX0", 
                # pack command template (tools/pack/<COMMAND>)
                ("zx0", "-f", "{filein}", "{fileout}"),
                # relocatable unpacker (tools/pack/a8/<UNPACKER>) and DECOMP_TO, COMP_DATA rel. tables
                ("zx0unpack.obj", (b"\x01\x80\x00", b"\x04\x80\x00"))
              ),
    PACK_LZ4: ("LZ4", ("TBD", "{filein}", "{fileout}"), ("TBD", (b"", b""))),
    PACK_APL: ("APL", ("TBD", "{filein}", "{fileout}"), ("TBD", (b"", b""))),
}


class Segment:

    def __init__(self, type, start=0, end=0):
        self.type = type
        self.start = start
        self.end = end
        self.packer = -1
        self.decomp_offset = 0
        self.data = None
        self.source = None # original/source segment for which pack() was called


    def len(self):
        return 1+self.end-self.start


    def datalen(self):
        return len(self.data) if self.data is not None else 0


    def init_addr(self):
        if self.start <= 0x2E2 and self.end >= 0x2E3:
            of = 0x2E2 - self.start
            init_addr = struct.unpack('<H', self.data[of:2+of])[0]
        else:
            init_addr = None
        return init_addr


    def run_addr(self):
        if self.start <= 0x2E0 and self.end >= 0x2E1:
            of = 0x2E0 - self.start
            run_addr = struct.unpack('<H', self.data[of:2+of])[0]
        else:
            run_addr = None
        return run_addr


    def hint_byte(self):
        if self.start <= 0x2DF and self.end >= 0x2DF:
            of = 0x2DF - self.start
            hint = self.data[of]
        else:
            hint = None
        return hint


    def write(self, fout):
        if self.type == SEGMENT_SIGNATURE:
            self.write_data(fout)
        elif self.type == SEGMENT_DATA:
            fout.write(struct.pack('<H', self.start))
            fout.write(struct.pack('<H', self.end))
            self.write_data(fout)
        elif self.type == SEGMENT_PACKED:
            fout.write(struct.pack('<H', self.start))
            fout.write(struct.pack('<H', self.end))
            fout.write(struct.pack('B', self.packer))
            self.write_data(fout)


    def write_data(self, fout):
        if self.data is not None:
            fout.write(self.data)


    def pack(self, packer, tempfilename=None):
        if self.type != SEGMENT_DATA:
            print(f"pack: bad segment type {self.type}")
            return None
        pn, cmd_template, up_template = packers.get(packer, (None, None, None))
        if cmd_template is None:
            print(f"pack: unknown packer {packer:02X}")
            return None
        tmpin = f"tmp-{self.start:04X}" if tempfilename is None else tempfilename
        tmpout = tmpin+"."+pn
        cmd = [arg.format(filein=tmpin, fileout=tmpout) for arg in cmd_template]
        cmd[0] = os.path.join(os.path.dirname(__file__), "pack", cmd[0])
        segment = None
        out = None
        with open(tmpin, 'wb') as fout:
            self.write_data(fout)
        try:
            out = subprocess.check_output(cmd, universal_newlines=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            print(e)
        if out is not None:
            delta = 32 # TODO
            if packer == PACK_ZX0:
                g = re.search("\(delta (\d+)\)", out)
                if g:
                    delta = int(g[1])
            data = None
            with open(tmpout, 'rb') as fin:
                data = fin.read()
            if data is not None:
                segment = Segment(SEGMENT_PACKED, self.start, 0)
                segment.packer = packer
                segment.data = data
                segment.decomp_offset = self.len() - len(data) + delta
                segment.source = self
            os.unlink(tmpout)
        os.unlink(tmpin)
        return segment


    def relocate(self, offset, table, header=True):
        # print(offset, table)
        # create relocated segment
        if header:
            # update load start/end addresses in segment header
            segment = Segment(self.type, self.start + offset, self.end + offset)
        else:
            # keep original addresses for RUN and INIT segments
            segment = Segment(self.type, self.start, self.end)
        segment.source = self
        # copy data bytes
        segment.data = bytearray(self.data)
        # do relocation
        rel = -1 # relocation "pointer" to data
        ti = 0   # relocation table index
        while ti < len(table):
            ro = table[ti] # relative relocation offset
            ti += 1
            if ro == 0:
                # 0 = end of table, relocation is done
                break
            if ro == 255:
                # update pointer, get next relative offset
                rel += 254
                continue
            # update pointer by relative offset
            rel += ro
            # get relocation type byte: REL_WORD, REL_LOW, REL_High
            if ti >= len(table):
                print("Unexpected end of relocation table")
                break
            rtype = table[ti]
            ti += 1
            if rtype == REL_WORD:
                # update word
                w = struct.unpack('<H', segment.data[rel:rel+2])[0]
                w = (w + offset) & 0xFFFF
                segment.data[rel] = w & 0xFF
                segment.data[rel+1] = w >> 8
            elif rtype == REL_LOW:
                # update low byte
                b = segment.data[rel]
                b = (b + offset) & 0xFF
                segment.data[rel] = b
            elif rtype == REL_HIGH:
                # update high byte
                if ti >= len(table):
                    print("Unexpected end of relocation table")
                    break
                # build original word, get low byte from table
                w = segment.data[rel] << 8 | table[ti]
                ti += 1
                # apply offset
                w = (w + offset) & 0xFFFF
                # store high byte
                segment.data[rel] = w >> 8
        return segment


class Ranges:

    def __init__(self):
        self.ranges = []

    def contains(self, addr):
        for r in self.ranges:
            if r[0] <= addr <= r[1]:
                return True
        return False

    def add(self, start, end):
        self.ranges.append((start, end))


class AtariDosObject:

    def __init__(self):
        self.segments = []


    def read_segment(self, fin):
        w = fin.read(2)
        if not w:
            return None

        block_start = struct.unpack('<H', w)[0]
        if block_start == 0xffff:
            s = Segment(SEGMENT_SIGNATURE)
            s.data = b'\xff\xff'
            return s

        w = fin.read(2)
        block_end = struct.unpack('<H', w)[0]
        if block_end == 0:
            s = Segment(SEGMENT_PACKED, block_start, block_end)
            b = fin.read(1)
            s.packer = b[0]
            s.data = fin.read()
            return s

        s = Segment(SEGMENT_DATA, block_start, block_end)
        s.data = fin.read(1+block_end-block_start)
        return s


    def load(self, filename):
        print(f'Reading file "{filename}"')
        self.segments = []
        with open(filename, 'rb') as fin:
            s = self.read_segment(fin)
            while s:
                self.segments.append(s)
                s = self.read_segment(fin)
        return self


    def save(self, filename):
        print(f'Writing file "{filename}"')
        with open(filename, 'wb') as fout:
            for s in self.segments:
                s.write(fout)
        return self


    def merge(self, obj):
        for s in obj.segments:
            if s.type != SEGMENT_SIGNATURE:
                self.segments.append(s)
        return self


    def pack(self, packer, min_size=128):
        packer_name = packers.get(packer, (None, None))[0]
        if packer_name is None:
            print(f"Packing segments - unknown packer ({packer})")
            return None
        print(f"Packing segments with {packer_name} ({packer})")
        obj = AtariDosObject()
        for i, s in enumerate(self.segments):
            if s.type == SEGMENT_DATA and s.len() >= min_size:
                print(f"Segment {i}:")
                s2 = s.pack(PACK_ZX0)
                if s2:
                    obj.segments.append(s2)
                    print(f"    {s.len()} -> {s2.datalen()}"
                        f", reduced by {s.len()-s2.datalen()} bytes ({100*s2.datalen()/s.len():2.1f}%)"
                )
                else:
                    print("Failed to pack segment")
            else:
                obj.segments.append(s)
        return obj


    def fix_init_order(self):
        """ATASM fix"""
        segments = self.segments
        output = []
        memory_ranges = Ranges()
        i = 0
        while i < len(segments):
            s = segments[i]
            if s.type == SEGMENT_DATA:
                if s.init_addr() is not None:
                    # data segment with init address
                    if memory_ranges.contains(s.init_addr()):
                        # ok, init is referring already loaded range
                        output.append(s)
                        memory_ranges.add(s.start, s.end)
                    else:
                        # yield other segments until init address is in range
                        j = i + 1
                        while j < len(segments):
                            s2 = segments[j]
                            output.append(s2)
                            if s2.type == SEGMENT_DATA:
                                memory_ranges.add(s2.start, s2.end)
                                if memory_ranges.contains(s.init_addr()):
                                    break
                            j += 1
                        if j == len(segments):
                            print(f"Failed to fix placement of init segment {i}")
                        else:
                            print(f"Fixed placement of init segment {i}")
                        # then place init segment
                        output.append(s)
                        memory_ranges.add(s.start, s.end)
                        # append rest and restart
                        output.extend(segments[j+1:])
                        memory_ranges = Ranges()
                        i = 0
                        segments = output
                        output = []
                        continue
                else:
                    # data segment without init
                    output.append(s)
                    memory_ranges.add(s.start, s.end)
            else:
                if s.type == SEGMENT_SIGNATURE and i > 0:
                    print(f"Skipped signature segment {i}")
                else:
                    # other segment type, just append to output
                    output.append(s)
            i += 1
        # while
        obj = AtariDosObject()
        obj.segments = output
        return obj


    def relocate(self, addr):
        """Relocate segments using segments with relocation table"""
        obj = AtariDosObject()
        i = 0
        offset = 0
        while i < len(self.segments):
            s = self.segments[i]
            # test if relocation hint and relocation table follows this segment
            if i+2 < len(self.segments) and self.segments[i+1].hint_byte() == 2:
                # yes, we can relocate
                if s.init_addr() is None and s.run_addr() is None:
                    # calculate offset
                    offset = addr - s.start
                    # relocate start/end addresses in segment header
                    hdr = True
                    print(f"Relocating segment {i} ({s.start:04X}->{addr:04X} offset {offset:04X}) with table from segment {i+2}")
                else:
                    # INIT or/and RUN segment
                    hdr = False
                    # use previous offset
                    print(f"Relocating segment {i} ({s.start:04X}->{s.start:04X} offset {offset:04X}) with table from segment {i+2}")
                s = s.relocate(offset, self.segments[i+2].data, hdr)
                # skip hint and table segments
                i += 2
            obj.segments.append(s)
            # next segment
            i += 1
        return obj


    def hybridize(self, stop_run=True):
        """Make packed segments DOS friendly"""
        obj = AtariDosObject()
        run_addr = None
        unpack = []
        # due to current limits in unpacker pick just segment with most bytes saved by compression
        max_saved = 0
        candidate = -1
        for i,s in enumerate(self.segments):
            if s.type == SEGMENT_PACKED:
                saved = s.source.datalen() - s.datalen()
                if saved > max_saved:
                    candidate = i
                    max_saved = saved
        if (candidate >= 0):
            print(f"Preparing hybrid ZX0/DOS file with packed segment {candidate}")
        for i,s in enumerate(self.segments):
            if s.type == SEGMENT_PACKED:
                if i == candidate:
                    print(f"Hybridizing packed segment {i}")
                    s2 = Segment(SEGMENT_DATA, 0x2DF, 0x2E1)
                    # LOAD w/ UNPACK
                    s2.data = b'\x01' + struct.pack('<H', s.start)
                    obj.segments.append(s2)
                    load_addr = s.start + s.decomp_offset
                    s3 = Segment(SEGMENT_DATA, load_addr, load_addr + s.datalen() - 1 + 1) # 1 byte packer code
                    s3.data = struct.pack('B', s.packer) + s.data
                    obj.segments.append(s3)
                    # keep list of segments which needs to be unpacked
                    unpack.append((s, s3))
                else:
                    print(f"Reverting to unpacked segment {i}")
                    obj.segments.append(s.source)
            elif s.type == SEGMENT_DATA and s.run_addr() is not None:
                run_addr = s.run_addr()
                if stop_run:
                    # check if we can skip or reduce segment with RUN address
                    if s.start == 0x2E0 or s.end == 0x2E1:
                        if s.len() > 2:
                            # reduce segment with RUN address
                            if s.start == 0x2E0:
                                s2 = Segment(SEGMENT_DATA, s.start+2, s.end)
                                s2.data = s.data[2:]
                            else:
                                s2 = Segment(SEGMENT_DATA, s.start, s.end-2)
                                s2.data = s.data[:-2]
                            obj.segments.append(s2)
                        else:
                            # skip segment with just RUN address
                            pass
                    else:
                        obj.segments.append(s)
                else:
                    obj.segments.append(s)
            else:
                obj.segments.append(s)
        if stop_run and run_addr is not None:
            # append STOP & RUN segment
            s = Segment(SEGMENT_DATA, 0x2DF, 0x2E1)
            s.data = b'\x00' + struct.pack('<H', run_addr)
            obj.segments.append(s)
        # append unpacker and call it for all packed segments
        if unpack:
            print("Appending unpacker")
            packer = unpack[0][0].packer
            pn, cmd_template, un_template = packers.get(packer, (None, None, None))
            unpacker_name = un_template[0]
            unpacker_addr = max([s.end+1 for s in obj.segments])
            unpacker_file = os.path.join(os.path.dirname(__file__), "pack", "a8", unpacker_name)
            unpacker = AtariDosObject().load(unpacker_file).relocate(unpacker_addr)
            # TODO better!
            # modify decompressor segment, set parameters COMP_DATA and DECOMP_TO
            # set DECOMP_TO, i.e. relocate 0xFFFF (-1) placeholder to RUNAD in segment 1
            unpacker_code_segment = unpacker.segments[1]
            unpack_to = unpack[0][0].start
            unpack_from = unpack[0][1].start
            print(f"Patch unpacker: unpack to {unpack_to:04X}")
            unpacker_code_segment = unpacker_code_segment.relocate(1 + unpack_to, un_template[1][0], header=False)
            # set COMP_DATA, i.e. relocate 0xFFFF (-1) placeholder to start of segment 2
            print(f"Patch unpacker: unpack from {unpack_from:04X}")
            unpacker_code_segment = unpacker_code_segment.relocate(1 + unpack_from, un_template[1][1], header=False)
            unpacker.segments[1] = unpacker_code_segment
            # TODO add more segments if more segments needs to be decompressed:
            # re-load COMP_DATA and DECOMP_TO parameters, add INIT to call unpacker
            obj.merge(unpacker)
        return obj


    def print_info(self):
        data_bytes = 0
        control_bytes = 0
        print("\nFile segments")
        for i,s in enumerate(self.segments):
            if s.type == SEGMENT_SIGNATURE:
                control_bytes += 2
                print(f"Segment {i}: {s.type} {struct.unpack('<H', s.data)[0]:04X}")

            elif s.type == SEGMENT_DATA:
                control_bytes += 4
                data_bytes += s.len()

                init_addr = s.init_addr()
                init_text = "" if init_addr is None else f" INIT {init_addr:04X}"

                run_addr = s.run_addr()
                hint_byte = s.hint_byte()
                run_text = ""
                if hint_byte == 2:
                    run_text = " RELOCATE"
                if run_addr is not None:
                    if hint_byte is None:
                        run_text = f" RUN {run_addr:04X}"
                    else:
                        if hint_byte == 0:
                            run_text = f" STOP & RUN {run_addr:04X}"
                        elif hint_byte == 1:
                            run_text = f" LOAD w/ UNPACK {run_addr:04X}"

                print(f"Segment {i}: {s.type} {s.start:04X}-{s.end:04X}"
                    f" {s.len()} bytes{init_text}{run_text}"
                )

            elif s.type == SEGMENT_PACKED:
                control_bytes += 5
                data_bytes += s.datalen()
                p = packers.get(s.packer)
                pname = p[0] if p else "unknown"
                print(f"Segment {i}: {s.type} {s.start:04X}-{s.end:04X}"
                    f" with {pname} ({s.packer:02X})"
                    f" {s.datalen()} bytes"
                )
        print(f"Total segments: {len(self.segments)}  Total bytes: {control_bytes+data_bytes}\n")


def main():
    o_verbose = False
    o_initfix = False
    a_filein = None
    a_fileout = None
    action = ''

    for arg in sys.argv[1:]:
        if arg == '-v':
            o_verbose = True
        elif arg == '-f':
            o_initfix = True
        elif arg == '-i':
            action = 'info'
        elif arg == '-c':
            action = 'pack'
        elif arg == '-d':
            action = 'packhybrid'
        elif arg == '-h':
            action = 'help'
        elif arg[0] == '-':
            print(f'Unknown option: "{arg}"')
            sys.exit(1)
        else:
            if a_filein is None:
                a_filein = arg
            elif a_fileout is None:
                a_fileout = arg
            else:
                print(f'Extra parameter: "{arg}"')
                sys.exit(1)

    if not action:
        action = 'initfix' if o_initfix else 'help'

    if action == 'help':
        print_help()
        sys.exit(0)
    elif action == 'pack' or action == 'packhybrid':
        if a_filein is None or a_fileout is None:
            print("To compress a file an input and output file names must be specified.")
            sys.exit(1)
    elif a_filein is None: # action == 'info'
        print("Input file names must be specified.")
        sys.exit(1)

    # read input file
    obj = AtariDosObject().load(a_filein)

    #
    # perfrom action
    #
    if action == 'info':
        obj.print_info()

    elif action == 'initfix':
        if o_verbose:  obj.print_info()

        obj = obj.fix_init_order()
        if o_verbose: obj.print_info()

        obj.save(a_fileout)

    elif action == 'pack':
        if o_verbose:  obj.print_info()

        if o_initfix:
            obj = obj.fix_init_order()
            if o_verbose: obj.print_info()

        obj = obj.pack(PACK_ZX0)
        if o_verbose: obj.print_info()

        obj.save(a_fileout)

    elif action == 'packhybrid':
        if o_verbose:  obj.print_info()

        if o_initfix:
            obj = obj.fix_init_order()
            if o_verbose: obj.print_info()

        obj = obj.pack(PACK_ZX0)
        if o_verbose: obj.print_info()

        obj = obj.hybridize()
        if o_verbose: obj.print_info()

        obj.save(a_fileout)


def print_help():
    print("""Packer for Atari 8-bit. Use to compress segmented Atari DOS files.
Usage: a8pack.py [options] input_file [output_file]
  -i      Print file info
  -c      Compress file segments
          to load a file a special loader which supports decompression is needed
  -d      Compress file segments, append decompression routine
          produced file is in Atari DOS compatible format
  -f      Fix order of INIT segments (for files produced by ATASM)
          Can be combined with -c or -d
  -v      Verbose output
  -h      Print this help
""")


if __name__ == '__main__':
    main()
