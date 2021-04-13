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
import struct
import subprocess
import os

SEGMENT_SIGNATURE = 'SIGNATURE' # 0xffff
SEGMENT_DATA = 'DATA'           # standard data block with: start,end,data[1+end-start]
SEGMENT_PACKED = 'PACKED'       # compressed data: start,0x0000,packer method (1 byte),data[unknown length when saved]

PACK_LZ4 = 0x00
PACK_APL = 0x01
PACK_ZX0 = 0x02

packers = {
    # packer code: name, packer command
    PACK_LZ4: ("LZ4", ("TBD", "{filein}", "{fileout}")),
    PACK_APL: ("APL", ("TBD", "{filein}", "{fileout}")),
    PACK_ZX0: ("ZX0", ("packers/zx0", "-f", "{filein}", "{fileout}")),
}


class Segment:

    def __init__(self, type, start=0, end=0):
        self.type = type
        self.start = start
        self.end = end
        self.packer = -1
        self.decomp_offset = 0
        self.data = None


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
        cmd_template = packers.get(packer, (None, None))[1]
        if cmd_template is None:
            print(f"pack: unknown packer {packer:02X}")
            return None
        tmpin = "0.dat" if tempfilename is None else tempfilename
        tmpout = tmpin+".zx0"
        cmd = [arg.format(filein=tmpin, fileout=tmpout) for arg in cmd_template]
        segment = None
        out = None
        with open(tmpin, 'wb') as fout:
            self.write_data(fout)
        try:
            out = subprocess.check_output(cmd, universal_newlines=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            print(e)
        if out is not None:
            # print(out)
            data = None
            with open(tmpout, 'rb') as fin:
                data = fin.read()
            if data is not None:
                segment = Segment(SEGMENT_PACKED, self.start, 0)
                segment.packer = packer
                segment.data = data
                segment.decomp_offset = self.len() - len(data) + 3 # TODO get offset from packer
            os.unlink(tmpout)
        os.unlink(tmpin)
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


    def hybridize(self, stop_run=True):
        """Make packed segments DOS friendly"""
        obj = AtariDosObject()
        run_addr = None
        for i,s in enumerate(self.segments):
            if s.type == SEGMENT_PACKED:
                print(f"Hybridizing packed segment {i}")
                s2 = Segment(SEGMENT_DATA, 0x2DF, 0x2E1)
                # LOAD w/ UNPACK
                s2.data = b'\x01' + struct.pack('<H', s.start)
                obj.segments.append(s2)
                load_addr = s.start + s.decomp_offset
                s3 = Segment(SEGMENT_DATA, load_addr, load_addr + s.datalen() - 1 + 1) # 1 byte packer code
                s3.data = struct.pack('B', s.packer) + s.data
                obj.segments.append(s3)
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
        return obj


    def print_info(self):
        data_bytes = 0
        control_bytes = 0
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
                if run_addr is None:
                    run_text = ""
                else:
                    hint_byte = s.hint_byte()
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
                control_bytes += 4
                data_bytes += s.datalen()
                p = packers.get(s.packer)
                pname = p[0] if p else "unknown"
                print(f"Segment {i}: {s.type} {s.start:04X}-{s.end:04X}"
                    f" with {pname} ({s.packer:02X})"
                    f" {s.datalen()} bytes"
                )
        print(f"Total segments: {len(self.segments)}  Total bytes: {control_bytes+data_bytes}\n")


def main():
    input_fname = sys.argv[1]
    output_fname = sys.argv[2]

    obj = AtariDosObject().load(input_fname)
    obj.print_info()

    obj = obj.fix_init_order()
    obj.print_info()

    obj = obj.pack(PACK_ZX0)
    obj.print_info()

    obj = obj.hybridize()
    obj.print_info()

    obj.save(output_fname)


if __name__ == '__main__':
    main()

