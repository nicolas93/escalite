#!/usr/bin/env python3

#    This file is part of Escalite.
#
#    Escalite is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Escalite is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Escalite.  If not, see <http://www.gnu.org/licenses/>.

#    2019-2020, Nicolas Schickert, TU Darmstadt
#    github.com/nicolas93/escalite

import argparse
import binascii
import math
import os
import string
import pydoc
import struct

colorred = "\x1B[31m"
colorgreen = "\x1B[32m"
coloryellow = "\x1B[33m"
colorblue = "\x1B[34m"
coloroff = "\x1B[0m"

Digraph = None
nohtml = None


class Header:
    """Class containing the information about the sqlite header"""
    headerbytes = b""

    def __init__(self, headerbytes):
        self.headerbytes = headerbytes

    def get_ascii_string(self):
        return self.headerbytes[0:16].decode(), self.headerbytes[0:16]

    def get_page_size(self):
        # 2^x, where x can be value between 9 and 15. if x = 0 -> 2^16
        num = int.from_bytes(self.headerbytes[16:18], "big", signed=False)
        if(num == 1):
            num = 65536
        elif(num < 512 or (math.log(num, 2) % 1 > 0)):
            print(colorred+"Non-standard page size!"+coloroff)
        return num, self.headerbytes[16:18]

    def get_file_format_write_version(self):
        return self.headerbytes[18], self.headerbytes[18]

    def get_file_format_read_version(self):
        return self.headerbytes[19], self.headerbytes[19]

    def get_file_reserved_bytes(self):
        return self.headerbytes[20], self.headerbytes[20]

    def get_change_count(self):
        num = int.from_bytes(self.headerbytes[24:28], "big", signed=False)
        return num, self.headerbytes[24:28]

    def get_db_size(self):
        # Why is the max-value 2**31-2 if there are 32 bytes used? this would indicate, that the size is signed, which doesnt make any sense
        num = int.from_bytes(self.headerbytes[28:32], "big", signed=False)
        if(num > 0x7ffffffe):
            print("Non-standard database size!")
        return num, self.headerbytes[28:32]

    def get_first_free_page(self):
        num = int.from_bytes(self.headerbytes[32:36], "big", signed=False)
        return num, self.headerbytes[32:36]

    def get_count_free_pages(self):
        num = int.from_bytes(self.headerbytes[36:40], "big", signed=False)
        return num, self.headerbytes[36:40]

    def get_auto_vacuum_mode(self):
        return self.headerbytes[52:56], self.headerbytes[52:56]

    def get_encoding(self):
        return self.headerbytes[56:60], self.headerbytes[56:60]

    def get_vacuum_mode(self):
        return self.headerbytes[64:68], self.headerbytes[64:68]

    def get_version_number(self):
        return self.headerbytes[96:100], self.headerbytes[96:100]

    def info(self, proof):
        s = coloryellow + "HEADER Information:\n"
        s += "\tSignatur: %s\n" % (self.get_ascii_string()[0])
        s += "\tVersion: %s\n" % binascii.hexlify(
            self.get_version_number()[1]).decode()
        s += "\tPage Size: %d\n" % self.get_page_size()[0]
        s += "\tDB Size(Pages): %d\n" % self.get_db_size()[0]
        s += "\tDB Size(Bytes): %d\n" % (self.get_page_size()
                                         [0] * self.get_db_size()[0])
        s += "\tChange count: %d\n" % self.get_change_count()[0]
        s += "\tFree Pages: %d\n" % self.get_count_free_pages()[0]
        s += "\tFirst free page: %d\n" % self.get_first_free_page()[0]
        s += "\tAuto vaccuum: %s\n" % binascii.hexlify(
            self.get_auto_vacuum_mode()[1]).decode()
        s += "\tVaccuum mode: %s\n" % binascii.hexlify(
            self.get_vacuum_mode()[1]).decode()
        s += coloroff
        return s


class FreeTrunkPage:
    """Class containing Information of a freelist trunk page."""
    pagebytes = b""

    def __init__(self, pagebytes):
        self.pagebytes = pagebytes

    def get_next_trunk_page(self):
        num = int.from_bytes(self.pagebytes[0:4], "big", signed=False)
        return num, self.pagebytes[0:4]

    def get_pointer_count(self):
        num = int.from_bytes(self.pagebytes[4:8], "big", signed=False)
        return num, self.pagebytes[4:8]

    def get_pointer(self, n):
        if(n > self.get_pointer_count()[0]):
            print("There are supposed to be only %d pointer. Weird." %
                  self.get_pointer_count()[0])
        pointer = (4 * n) + 8
        num = int.from_bytes(
            self.pagebytes[pointer:pointer+4], "big", signed=False)
        return num, self.pagebytes[pointer:pointer+4]

    def get_cells(self):
        cells = []
        for i in range(0, self.get_pointer_count()[0]):
            cells.append("%d" % self.get_pointer(i)[0])
        s = " | ".join(cells)
        print(s)
        return s

    def info(self):
        s = "FreeList Trunk Page Information:\n"
        s += "\tNext trunk page: %d\n" % self.get_next_trunk_page()[0]
        s += "\t#Leaves: %d\n" % self.get_pointer_count()[0]
        s += "\tLeaves:\n"
        if(self.get_pointer_count()[0] > 2000 or (self.get_pointer_count()[0] >= 3 and self.get_pointer(0)[0] == 0 and self.get_pointer(1)[0] == 0 and self.get_pointer(2)[0])):
            s += colorred + "\tThere are to many leaves or the first three leaves are null. This does not seem like a freelist trunk page.\n"
            s += "\tUse pd <n> to investigate further." + coloroff
            return s
        values = [""] * 8
        for i in range(0, self.get_pointer_count()[0]):
            values[i % 8] = "%d" % self.get_pointer(i)[0]
            if(i % 8 == 7 and i > 0):
                s += "\t\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % (
                    values[0], values[1], values[2], values[3], values[4], values[5], values[6], values[7])
                values = [""] * 8
        else:
            i += 1
            if(i % 8 != 0 and i > 0):
                s += "\t\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % (
                    values[0], values[1], values[2], values[3], values[4], values[5], values[6], values[7])
        return s


class FreeLeafPage:
    """Class containing a freelist leaf page. Should contain no information."""
    pagebytes = b""

    def __init__(self, pagebytes):
        self.pagebytes = pagebytes

    def check(self):
        for b in self.pagebytes:
            if(b != b"\x00"):
                return "Freelist leaf page still contains information!", False
        return "Freelist leaf page is clear.", True

    def dump_page(self):
        c = 1
        hexstr = ""
        asciistr = ""
        color = ""
        text = ""
        for b in self.pagebytes:
            if(b != 0):
                color = colorred
            else:
                color = ""
            hexstr += "%s%02x %s" % (color, b, coloroff)
            if(chr(b) in string.printable and b >= 0x20):
                asciistr += chr(b)
            else:
                asciistr += "."
            if(c % 16 == 0 and c != 0):
                text += ("%08x : %s\t\t %s\n" % (c-16, hexstr, asciistr))
                hexstr = ""
                asciistr = ""
            c += 1
        if(c % 16 != 0):
            hexstr += "   " * (16 - (c % 16))
            asciistr += " " * (16 - (c % 16))
            text += ("%08x : %s\t\t %s\n" % (c-16, hexstr, asciistr))
        return text


class BTreePage:
    """Class containing a b tree page."""

    pagebytes = b""
    number = 0
    negoffset = 0
    totaloffset = 0

    def __init__(self, pagebytes, number, totaloffset, negoffset=0):
        self.pagebytes = pagebytes
        self.number = number
        self.negoffset = negoffset
        self.totaloffset = totaloffset

    def get_pagetype(self):
        if(self.pagebytes[0] == 0x02):
            return "Interior, Index", self.pagebytes[0]
        elif(self.pagebytes[0] == 0x05):
            return "Interior, Table", self.pagebytes[0]
        elif(self.pagebytes[0] == 0x0a):
            return "Leaf, Index", self.pagebytes[0]
        elif(self.pagebytes[0] == 0x0d):
            return "Leaf, Table", self.pagebytes[0]
        else:
            return "Unknown 0x%02x" % self.pagebytes[0], self.pagebytes[0]

    def get_first_free_cell(self):
        num = int.from_bytes(self.pagebytes[1:3], "big", signed=False)
        return num, self.pagebytes[1:3]

    def get_cellcount(self):
        num = int.from_bytes(self.pagebytes[3:5], "big", signed=False)
        return num, self.pagebytes[3:5]

    def get_datastart(self):
        num = int.from_bytes(self.pagebytes[5:7], "big", signed=False)
        return num, self.pagebytes[5:7]

    def get_fragment_count(self):
        num = int.from_bytes(self.pagebytes[7:8], "big", signed=False)
        return num, self.pagebytes[7:8]

    def get_last_child_pointer(self):
        num = int.from_bytes(self.pagebytes[8:12], "big", signed=False)
        return num, self.pagebytes[8:12]

    def get_tree_childs(self):
        childs = []
        if(self.pagebytes[0] == 0x02 or self.pagebytes[0] == 0x05):
            print("a")
            cell_array_pointer = 12
            cell_array_end = (self.get_cellcount()[0] * 2) + 12
            print(cell_array_pointer)
            print(cell_array_end)
            while(cell_array_end > cell_array_pointer):
                num = int.from_bytes(
                    self.pagebytes[cell_array_pointer:cell_array_pointer+2], "big", signed=False)
                cell_array_pointer += 2
                child = int.from_bytes(
                    self.pagebytes[num-self.negoffset:num-self.negoffset+4], "big", signed=False)
                childs.append(child)
            childs.append(self.get_last_child_pointer()[0])
        return childs

    def info(self):
        s = colorblue + "BTree Page Information:\n"
        s += "\tPage Number: %d\n" % self.number
        s += "\tPage type: %s\n" % (self.get_pagetype()[0])
        s += "\tFirst free block: %d\n" % self.get_first_free_cell()[0]
        s += "\tCell count: %d\n" % self.get_cellcount()[0]
        s += "\tData Start: %d\n" % self.get_datastart()[0]
        s += "\tFragment count: %d\n" % self.get_fragment_count()[0]
        if(self.get_pagetype()[1] < 0xa):
            s += "\tLast Child: %d\n" % self.get_last_child_pointer()[0]
        s += coloroff
        return s

    def check(self):
        # is area between cell array and data really empty?
        last_cell_pointer = self.get_cellcount(
        )[0] * 4 + 12 + (0 if(self.pagebytes[0] != 0x02 and self.pagebytes[0] != 0x05) else 4)
        data_start = self.get_datastart()[0]
        for b in self.pagebytes[last_cell_pointer:data_start-self.negoffset]:
            if b != 0:
                print("Contains undeleted data!!")
                print(self.dump_page())
                return
        print("Page OK.")

    def read_data(self):
        cell_array_pointer = 8
        cell_array_end = (self.get_cellcount()[0] * 2) + 8
        if(self.pagebytes[0] == 0x2 or self.pagebytes[0] == 0x5):
            cell_array_pointer += 4
            cell_array_end += 4
        while(cell_array_end > cell_array_pointer):
            num = int.from_bytes(
                self.pagebytes[cell_array_pointer:cell_array_pointer+2], "big", signed=False)
            print("\tCELL at offset: 0x%06x" % num)
            cell_array_pointer += 2
            self.read_cell(num)
            print("\n")

    def read_data_master(self):
        if(self.pagebytes[0] != 0xd):
            print("Multipage master-tables are not yet implemented")
            return [], []
        cell_array_pointer = 8
        cell_array_end = (self.get_cellcount()[0] * 2) + 8
        tablenames = []
        tablepagenrs = []
        if(self.pagebytes[0] == 0x2 or self.pagebytes[0] == 0x5):
            cell_array_pointer += 4
            cell_array_end += 4
        while(cell_array_end > cell_array_pointer):
            num = int.from_bytes(
                self.pagebytes[cell_array_pointer:cell_array_pointer+2], "big", signed=False)
            print("\tCELL at offset: 0x%06x" % num)
            cell_array_pointer += 2
            name, pagenr = self.read_cell_master(num)
            tablenames.append(name)
            tablepagenrs.append(pagenr)
            print("\n")
        return tablenames, tablepagenrs

    def read_cell_master(self, start, intent=2):
        pointer = start - self.negoffset
        record_length_bytes = b""
        while(self.pagebytes[pointer] >= 0x80):
            record_length_bytes += self.pagebytes[pointer:pointer+1]
            pointer += 1
        record_length_bytes += self.pagebytes[pointer:pointer+1]
        pointer += 1
        print("\t"*intent + "Cell length: %d" %
              self.varint2int(record_length_bytes))

        id_bytes = b""
        while(self.pagebytes[pointer] >= 0x80):
            id_bytes += self.pagebytes[pointer:pointer+1]
            pointer += 1
        id_bytes += self.pagebytes[pointer:pointer+1]
        pointer += 1
        print("\t"*intent + "ID: %d" % self.varint2int(id_bytes))

        record_header_length_bytes = b""
        while(self.pagebytes[pointer] >= 0x80):
            record_header_length_bytes += self.pagebytes[pointer:pointer+1]
            pointer += 1
        record_header_length_bytes += self.pagebytes[pointer:pointer+1]
        pointer += 1
        print("\t"*intent + "Record header length: %d" %
              self.varint2int(record_header_length_bytes))

        types = []
        i = 0
        while(i < self.varint2int(record_header_length_bytes)-len(record_header_length_bytes)):
            type_bytes = b""
            while(self.pagebytes[pointer] >= 0x80):
                type_bytes += self.pagebytes[pointer:pointer+1]
                pointer += 1
                i += 1
            type_bytes += self.pagebytes[pointer:pointer+1]
            pointer += 1
            #print("\t"*intent + "Type: %s" % self.varint2int(type_bytes))
            types.append(self.varint2int(type_bytes))
            i += 1

        name = ""
        pagenr = 0
        for i, t in enumerate(types):
            string = ""
            value = 0
            if(t < 5):
                value = int.from_bytes(
                    self.pagebytes[pointer:pointer+t], "big", signed=True)
                pointer += t
            elif(t == 5):
                value = int.from_bytes(
                    self.pagebytes[pointer:pointer+6], "big", signed=True)
                pointer += 6
            elif(t == 6):
                value = int.from_bytes(
                    self.pagebytes[pointer:pointer+8], "big", signed=True)
                pointer += 8
            elif(t >= 12 and t % 2 == 0):
                length = int((t-12)/2)
                pointer += length
            elif(t >= 12 and t % 2 == 1):
                length = int((t-13)/2)
                string = self.pagebytes[pointer:pointer+length].decode()
                pointer += length
            if(i == 3):
                pagenr = value
            if(i == 1):
                name = string
        return name, pagenr

    def varint2int(self, vi):
        i = 0
        x = 0
        # print(vi[::-1])
        for b in vi[::-1]:
            #print("%d %d %d" % (i, x, b))
            if x == 0:
                i = b
            else:
                b = b ^ 0x80
                i += (2**(x*7)) * b
            x = x+1
        return i

    def read_cell(self, start, intent=2):
        pointer = start - self.negoffset
        record_length_bytes = b""
        while(self.pagebytes[pointer] >= 0x80):
            record_length_bytes += self.pagebytes[pointer:pointer+1]
            pointer += 1
        record_length_bytes += self.pagebytes[pointer:pointer+1]
        pointer += 1
        print("\t"*intent + "Cell length: %d" %
              self.varint2int(record_length_bytes))

        id_bytes = b""
        while(self.pagebytes[pointer] >= 0x80):
            id_bytes += self.pagebytes[pointer:pointer+1]
            pointer += 1
        id_bytes += self.pagebytes[pointer:pointer+1]
        pointer += 1
        print("\t"*intent + "ID: %d" % self.varint2int(id_bytes))

        record_header_length_bytes = b""
        while(self.pagebytes[pointer] >= 0x80):
            record_header_length_bytes += self.pagebytes[pointer:pointer+1]
            pointer += 1
        record_header_length_bytes += self.pagebytes[pointer:pointer+1]
        pointer += 1
        print("\t"*intent + "Record header length: %d" %
              self.varint2int(record_header_length_bytes))

        types = []
        i = 0
        while(i < self.varint2int(record_header_length_bytes)-len(record_header_length_bytes)):
            type_bytes = b""
            while(self.pagebytes[pointer] >= 0x80):
                type_bytes += self.pagebytes[pointer:pointer+1]
                pointer += 1
                i += 1
            type_bytes += self.pagebytes[pointer:pointer+1]
            pointer += 1
            #print("\t"*intent + "Type: %s" % self.varint2int(type_bytes))
            types.append(self.varint2int(type_bytes))
            i += 1

        for t in types: # See here for documentation: https://www.sqlite.org/fileformat.html
            if(t < 5):
                print("\t" * intent + "Type: %d (int) | Value: %d" %
                      (t, int.from_bytes(self.pagebytes[pointer:pointer+t], "big", signed=True)))
                pointer += t
            elif(t == 5):
                print("\t" * intent + "Type: %d (int) | Value: %d" %
                      (t, int.from_bytes(self.pagebytes[pointer:pointer+6], "big", signed=True)))
                pointer += 6
            elif(t == 6):
                print("\t" * intent + "Type: %d (int) | Value: %d" %
                      (t, int.from_bytes(self.pagebytes[pointer:pointer+8], "big", signed=True)))
                pointer += 8
            elif(t == 7):
                print("\t" * intent + "Type: %d (real) | Value %f" % (t, struct.unpack('>d',self.pagebytes[pointer:pointer+8])[0]))
                pointer += 8
            elif(t == 8):
                print("\t" * intent + "Type: %d (int) | Value: 0" %(t))
            elif(t == 9):
                print("\t" * intent + "Type: %d (int) | Value: 1" %(t))
            elif(t == 10 or t == 11):
                print("\t" * intent + "Type: %d | %sThis datatype is reserved for internal use and should not appear in regular SQLite databases!%s" % (t, colorred, coloroff))
                print("\t" * (2+intent) + "%sThe following offsets might be wrong and lead to wrong interpretations%s" % (colorred, coloroff))
            elif(t >= 12 and t % 2 == 0):
                length = int((t-12)/2)
                print("\t" * intent + "Type: BLOB    | Value: %s" %
                      self.pagebytes[pointer:pointer+length])
                pointer += length
            elif(t >= 12 and t % 2 == 1):
                length = int((t-13)/2)
                print("\t" * intent + "Type: String  | Value: %s" %
                      self.pagebytes[pointer:pointer+length].decode())
                pointer += length
            else:
                print("\t" * intent + "unknown: %d | That shouldnt be possible." %t)

        return 0

    def read_removed_data(self):
        freeblock = self.get_first_free_cell()[0] - self.negoffset
        if(freeblock == (0-self.negoffset)):
            print("\n\tNo free blocks to retrieve.")
        while(freeblock != (0-self.negoffset)):
            length = int.from_bytes(
                self.pagebytes[freeblock+2:freeblock+4], "big", signed=False)
            print("\tFree Block: \n\t\tOffset: 0x%06x\n\t\tLength: %06d\n\t\tData: " % (
                freeblock+self.negoffset, length) + binascii.hexlify(self.pagebytes[freeblock:freeblock+length]).decode())
            freeblock = int.from_bytes(
                self.pagebytes[freeblock:freeblock+2], "big", signed=False) - self.negoffset

    def dump_page(self):
        hexstr = ""
        asciistr = ""
        color = ""
        text = ""
        for i, b in enumerate(self.pagebytes):
            if((i < 8) or (i < 12 and (self.get_pagetype()[1] == 0x2 or self.get_pagetype()[1] == 0x5))):
                color = coloryellow
            elif(i >= self.get_datastart()[0] - self.negoffset):
                color = colorred
            else:
                color = ""
            hexstr += "%s%02x %s" % (color, b, coloroff)
            if(chr(b) in string.printable and b >= 0x20):
                asciistr += "%s%s%s" % (color, chr(b), coloroff)
            else:
                asciistr += "%s.%s" % (color, coloroff)
            if(i % 16 == 15):
                text += ("%08x : %s\t\t %s\n" %
                         (i-15 + self.negoffset, hexstr, asciistr))
                hexstr = ""
                asciistr = ""
        else:
            if(i % 16 != 15):
                hexstr += "   " * (16 - (i % 16))
                asciistr += " " * (16 - (i % 16))
                text += ("%08x : %s\t\t %s\n" %
                         (i-(i % 16) + self.negoffset, hexstr, asciistr))
        return text

    def shortinfo(self):
        s = "Page Nr.: %d, Offset: 0x%06x, Type: %s, Cells: %d, First free block: 0x%04x" % (
            self.number, self.totaloffset, self.get_pagetype()[0], self.get_cellcount()[0], self.get_first_free_cell()[0])
        return s


def analyzePage(header, page, pagenr, negoffset=0, proof=False):
    print("\n")
    print(page.info())
    page.check()


def showFreeList(header, pages):
    g = Digraph('g', filename='freelist.gv',
                node_attr={'shape': 'record', 'height': '.1'})
    f = header.get_first_free_page()[0]
    if(f != 0 and len(FreeTrunkPage(pages[f-1].pagebytes).get_cells()) != 0):
        if(len(FreeTrunkPage(pages[f-1].pagebytes).get_cells()) > 30):
            g.node('node%d' % f, nohtml('{<f%d> %d | Trunkpage } | %d Leaves' % (
                f, f, len(FreeTrunkPage(pages[f-1].pagebytes).get_cells()))))
        else:
            g.node('node%d' % f, nohtml('{<f%d> %d | Trunkpage } | %s' % (
                f, f, FreeTrunkPage(pages[f-1].pagebytes).get_cells())))
    else:
        g.node('node%d' % f, nohtml('<f%d> %d' % (f, f)))
    while(f != 0):
        print(f)
        nf = FreeTrunkPage(pages[f-1].pagebytes).get_next_trunk_page()[0]
        if(nf != 0):
            if(len(FreeTrunkPage(pages[f-1].pagebytes).get_cells()) > 30):
                g.node('node%d' % nf, nohtml('{<f%d> %d | Trunkpage } | %d Leaves' % (
                    nf, nf, len(FreeTrunkPage(pages[nf-1].pagebytes).get_cells()))))
            else:
                g.node('node%d' % nf, nohtml('{<f%d> %d | Trunkpage } | %s' % (
                    nf, nf, FreeTrunkPage(pages[nf-1].pagebytes).get_cells())))
        else:
            g.node('node%d' % nf, nohtml('<f%d> %d' % (nf, nf)))
        g.edge('node%d:f%d' % (f, f), 'node%d:f%d' % (nf, nf))
        f = nf
    g.view()


def showBTree(header, pages, start, name, g):
    childs = pages[start-1].get_tree_childs()
    g.node('node%d' % start, nohtml(
        '{BTree Root:%s | <f%d> %d}' % (name, start, start)))
    if(len(childs) > 0):
        print(childs)
        if not(len(pages[childs[0]-1].get_tree_childs()) > 0):
            childstring = "{<f%d> Leaves: | %d" % (childs[0], childs[0])
            for i, c in enumerate(childs[1:]):
                if(((i+1) % 16) == 0):
                    childstring += "| %d" % c
                else:
                    childstring += ", %d" % c
            childstring += "}"
            print(childstring)
            g.node('node%d' % childs[0], nohtml(childstring))
            g.edge('node%d:f%d' % (start, start), 'node%d:f%d' %
                   (childs[0], childs[0]))
        else:
            for c in childs:
                g = showBTreeSubNodes(header, pages, c, g)
                g.edge('node%d:f%d' % (start, start), 'node%d:f%d' % (c, c))


def showBTreeSubNodes(header, pages, start, g):
    childs = pages[start-1].get_tree_childs()
    g.node('node%d' % start, nohtml('<f%d> %d' % (start, start)))
    if(len(childs) > 0):
        print(childs)
        if not(len(pages[childs[0]-1].get_tree_childs()) > 0):
            childstring = "{<f%d> Leaves: | %d" % (childs[0], childs[0])
            for i, c in enumerate(childs[1:]):
                if(((i+1) % 16) == 0):
                    childstring += "| %d" % c
                else:
                    childstring += ", %d" % c
            childstring += "}"
            print(childstring)
            g.node('node%d' % childs[0], nohtml(childstring))
            g.edge('node%d:f%d' % (start, start), 'node%d:f%d' %
                   (childs[0], childs[0]))
            return g
    for c in childs:
        showBTreeSubNodes(header, pages, c, g)
    return g


def interactive(header, pages, overview, proof=False):
    exit = False
    global Digraph, nohtml
    while not exit:
        cmd = input("cmd:")
        cmdline = cmd.split(" ")
        if(len(cmd) == 0):
            print("'help' for help")
            continue
        if(cmdline[0] == "h"):
            try:
                print(header.info(proof))
            except Exception as e:
                print(e)
                print("Error with the header")
        if(cmdline[0] == "o"):
            try:
                pydoc.pipepager(
                    colorblue+"Showing overview of pages:\n"+coloroff+overview, cmd='less -R')
            except Exception as e:
                print(e)
                print("Error with the overview")
        if(cmdline[0] == "b"):
            try:
                from graphviz import Digraph, nohtml
                g = Digraph('g', filename='btree.gv', graph_attr={'splines': 'false'},
                            node_attr={'shape': 'record', 'height': '.1'})
                if(len(cmdline) == 1):
                    tablenames, tablepagenrs = pages[0].read_data_master()
                    print(tablepagenrs)
                    for i in range(0, len(tablenames)):
                        print("i:%d pagenr:%d name:%s" %
                              (i, tablepagenrs[i], tablenames[i]))
                        showBTree(header, pages,
                                  tablepagenrs[i], tablenames[i], g)
                else:
                    showBTree(header, pages, int(cmdline[1]), "Root", g)
                g.view()
            except Exception as e:
                print(e)
                print("Error with the btree")
        if(cmdline[0] == "p"):
            try:
                analyzePage(header, pages[int(
                    cmdline[1])-1], int(cmdline[1]), 0 if int(cmdline[1]) != 1 else 100)
            except Exception as e:
                print(e)
                print("Error with this page")
        if(cmdline[0] == "pr"):
            try:
                pages[int(cmdline[1])-1].read_removed_data()
            except Exception as e:
                print(e)
                print("Error with this page")
        if(cmdline[0] == "pc"):
            try:
                pages[int(cmdline[1])-1].read_data()
            except Exception as e:
                print(e)
                print("Error with this page")
        if(cmdline[0] == "pd"):
            try:
                data = pages[int(cmdline[1])-1].dump_page()
                if(len(data.split("\n")) <= 1000):
                    print(data)
                else:
                    pydoc.pipepager(data, cmd='less -R')
            except Exception as e:
                print(e)
                print("Error with this page")
        if(cmdline[0] == "f"):
            try:
                f = FreeTrunkPage(pages[int(cmdline[1])-1].pagebytes)
                print(f.info())
            except Exception as e:
                print("Error with this page")
                print(e)
        if(cmdline[0] == "fcl"):
            try:
                f = FreeLeafPage(pages[int(cmdline[1])-1].pagebytes)
                if not (f.check()[1]):
                    data = f.dump_page()
                    if(len(data.split("\n")) <= 1000):
                        print(data)
                    else:
                        pydoc.pipepager(data, cmd='less -R')
            except Exception as e:
                print("Error with this page")
                print(e)
        if(cmdline[0] == "fl"):
            try:
                from graphviz import Digraph, nohtml
                showFreeList(header, pages)
            except Exception as e:
                print("Error with the freelist")
                print(e)
        elif(cmdline[0] == "exit" or cmdline[0] == "q"):
            exit = True
        elif(cmdline[0] == "help"):
            print("Commands:")
            print("h\t\tShow header info")
            print("o\t\tShow overview of all pages")
            print("b <n>\t\tShow BTree graph (Starting at page n, Default n=2)")
            print("p <n>\t\tanalyze page <n> (As a normal BTree page)")
            print("pr <n>\t\tSearch removed data on page <n>")
            print("pc <n>\t\tPrint celldata on page <n>")
            print("pd <n>\t\tPrint hexdump of page <n>")
            print("f <n>\t\tanalyze page <n> (As a freelist trunk page)")
            print("fcl <n>\t\tCheck if freelist-leaf page <n> is empty")
            print("fl\t\tShow freelist graph")
            print("exit|q\t\texit")


def analyze(db, proof=False):
    headerbytes = db.read(100)
    offset = 100
    header = Header(headerbytes)
    print(header.info(proof))
    p = db.read(header.get_page_size()[0] - 100)
    b = BTreePage(p, 1, 100, offset)
    offset = header.get_page_size()[0]
    pages = [b]
    overview = b.shortinfo() + "\n"
    for i in range(2, header.get_db_size()[0]+1):
        p = db.read(header.get_page_size()[0])
        b = BTreePage(p, i, offset)
        if(b.get_pagetype()[1] == 0x00):
            f = FreeTrunkPage(b.pagebytes)
            overview += "Potential free-page, Offset: 0x%08x, Number: %d, Next Trunk: %d, #Leafes:%d\n" % (
                offset, i, f.get_next_trunk_page()[0], f.get_pointer_count()[0])
        else:
            overview += b.shortinfo() + "\n"
        offset += header.get_page_size()[0]
        pages.append(b)
    if(header.get_db_size()[0] > 30):
        pydoc.pipepager(colorblue+"Showing overview of pages:\n"+coloroff+overview, cmd='less -R')
    else:
        print(overview)
    interactive(header, pages, overview)


def main():
    parser = argparse.ArgumentParser(
        description='Examine the structure of a SQLite database and recover removed entries.')
    parser.add_argument("database", help="SQLite database file to be examined")
    parser.add_argument('--proof', action='store_true',
                        help="show proofs when possible (not yet implemented)")
    args = parser.parse_args()
    try:
        db = open(args.database, "rb")
    except OSError:
        print("Try using a database that actually exists.")
    else:
        print("Real file size: %d\n\n" % os.stat(args.database).st_size)
        analyze(db, args.proof)


if __name__ == "__main__":
    main()
