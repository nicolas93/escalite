#!/usr/bin/env python3
# 2019, Nicolas Schickert, TU Darmstadt



import argparse
import binascii
import math
import os
import string

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
		elif(num < 512 or (math.log(512,2)%1 >0)):
			print("Non-standard page size!")
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
		s = "HEADER Information:\n"
		s += "\tSignatur: %s\n" % (self.get_ascii_string()[0])
		s += "\tVersion: %s\n" % binascii.hexlify(self.get_version_number()[1]).decode()
		s += "\tPage Size: %d\n" % self.get_page_size()[0]
		s += "\tDB Size(Pages): %d\n" % self.get_db_size()[0]
		s += "\tDB Size(Bytes): %d\n" % (self.get_page_size()[0] * self.get_db_size()[0])
		s += "\tChange count: %d\n" % self.get_change_count()[0]
		s += "\tFree Pages: %d\n" % self.get_count_free_pages()[0]
		s += "\tFirst free page: %d\n" %self.get_first_free_page()[0]
		s += "\tAuto vaccuum: %s\n" % binascii.hexlify(self.get_auto_vacuum_mode()[1]).decode()
		s += "\tVaccuum mode: %s\n" % binascii.hexlify(self.get_vacuum_mode()[1]).decode()
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
			print("There are supposed to be only %d pointer. Weird." % self.get_pointer_count()[0])
		pointer = (4 * n) + 8
		num = int.from_bytes(self.pagebytes[n:n+4], "big", signed=False)
		return num, self.pagebytes[n:n+4]

class FreeLeafPage:
	"""Class containing a freelist leaf page. Should contain no information."""
	pagebytes = b""

	def __init__(self, pagebytes):
		self.pagebytes = pagebytes

	def check(self):
		for b in self.pagebytes:
			if(b != b"\x00"):
				return "Freelist leaf page still contains information!"
		return "Freelist leaf page is clear."

	def print_page(self):
		c = 1
		hexstr = ""
		asciistr = ""
		for b in self.pagebytes:
			hexstr += "%02x " % b
			if(chr(b) in string.printable and chr(b) != "\r"):
				asciistr += chr(b)
			else:
				asciistr += "."
			if(c % 16 == 0 and c != 0):
				print("%08x : %s\t\t %s" %(c-16, hexstr, asciistr))
				hexstr = ""
				asciistr = ""
			c += 1
		if(c % 16 != 0):
			hexstr += "   " * ( 16 - (c % 16))
			asciistr += " " * (16 - (c % 16))
			print("%08x : %s\t\t %s" %(c-16, hexstr, asciistr))

class BTreePage:
	"""Class containing a b tree page."""

	pagebytes = b""
	number = 0
	negoffset = 0

	def __init__(self, pagebytes, number, negoffset=0):
		self.pagebytes = pagebytes
		self.number = number
		self.negoffset = negoffset

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
			return "Unknown %02x" % self.pagebytes[0], self.pagebytes[0]

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

	def info(self):
		s = "BTree Page Information:\n"
		s += "\tPage Number: %d\n" % self.number
		s += "\tPage type: %s\n" % (self.get_pagetype()[0])
		s += "\tFirst free block: %d\n" % self.get_first_free_cell()[0]
		s += "\tCell count: %d\n" % self.get_cellcount()[0]
		s += "\tData Start: %d\n" % self.get_datastart()[0]
		s += "\tFragment count: %d\n" % self.get_fragment_count()[0]
		if(self.get_pagetype()[1] < 0xa):
			s += "\tLast Child: %d\n" % self.get_last_child_pointer()[0]
		return s

	def check(self):
		# TODO: is area between cell array and data really empty?
		pass

	def read_data(self):
		cell_array_pointer = 8
		cell_array_end = (self.get_cellcount()[0] * 2) + 8
		if(self.pagebytes[0] == 0x2 or self.pagebytes[0] == 0x5):
			cell_array_pointer += 4
			cell_array_end += 4
		while(cell_array_end > cell_array_pointer):
			num = int.from_bytes(self.pagebytes[cell_array_pointer:cell_array_pointer+2], "big", signed=False)
			print("\tCELL at offset: %06x" % num)
			cell_array_pointer += 2
			self.read_cell(num)
			print("\n")

	def varint2int(self, vi):
		i = 0
		x = 0
		#print(vi[::-1])
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
		print("\t"*intent + "Cell length: %d" % self.varint2int(record_length_bytes))

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
		print("\t"*intent + "Record header length: %d" % self.varint2int(record_header_length_bytes))
		
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

		for t in types:
			if(t < 5):
				print("\t" * intent + "Type: %d (int) | Value: %d" %(t, int.from_bytes(self.pagebytes[pointer:pointer+t], "big", signed=True)))
				pointer += t
			elif(t == 5):
				print("\t" * intent + "Type: %d (int) | Value: %d" %(t, int.from_bytes(self.pagebytes[pointer:pointer+6], "big", signed=True)))
				pointer += 6
			elif(t == 6):
				print("\t" * intent + "Type: %d (int) | Value: %d" %(t, int.from_bytes(self.pagebytes[pointer:pointer+8], "big", signed=True)))
				pointer += 8
			elif(t >= 12 and t%2==0):
				length = int((t-12)/2)
				print("\t"* intent +  "Type: BLOB    | Value: %s" % self.pagebytes[pointer:pointer+length])
				pointer += length
			elif(t >= 12 and t%2==1):
				length = int((t-13)/2)
				print("\t"* intent +  "Type: String  | Value: %s" % self.pagebytes[pointer:pointer+length].decode())
				pointer += length
			else:
				print("unknown")

		return 0

	def read_removed_data(self):
		freeblock = self.get_first_free_cell()[0] - self.negoffset
		if(freeblock == 0):
			print("\n\tNo free blocks to retrieve.")
		while(freeblock != 0):
			length = int.from_bytes(self.pagebytes[freeblock+2:freeblock+4], "big", signed=False)
			print("\tFree Block: \n\t\tOffset: %06x\n\t\tLength: %06d\n\t\tData: " %(freeblock, length) + binascii.hexlify(self.pagebytes[freeblock:freeblock+length]).decode())
			freeblock = int.from_bytes(self.pagebytes[freeblock:freeblock+2], "big", signed=False)


	def print_page(self):
		c = 1
		hexstr = ""
		asciistr = ""
		for b in self.pagebytes:
			hexstr += "%02x " % b
			if(chr(b) in string.printable and chr(b) != "\r"):
				asciistr += chr(b)
			else:
				asciistr += "."
			if(c % 16 == 0 and c != 0):
				print("%08x : %s\t\t %s" %(c-16, hexstr, asciistr))
				hexstr = ""
				asciistr = ""
			c += 1
		if(c % 16 != 0):
			hexstr += "   " * ( 16 - (c % 16))
			asciistr += " " * (16 - (c % 16))
			print("%08x : %s\t\t %s" %(c-16, hexstr, asciistr))





def analyzePage(db, header, pagenr, pagesize, negoffset=0, proof=False):
	pass


def analyze(db, proof=False):
	headerbytes = db.read(100)
	header = Header(headerbytes)
	print(header.info(proof))
	p = db.read(header.get_page_size()[0] -100)
	b = BTreePage(p, 1, 100)
	print(b.info())
	b.read_data()
	p = db.read(header.get_page_size()[0])
	b = BTreePage(p, 2)
	print(b.info())
	b.read_data()
	b.read_removed_data()



def main():
	parser = argparse.ArgumentParser(description='Find main colors in a given image.')
	parser.add_argument("database", help="SQLite database file to be examined")
	parser.add_argument('--proof', action='store_true', help="show proofs when possible")
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
