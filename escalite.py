#!/usr/bin/env python3
# 2019, Nicolas Schickert, TU Darmstadt



import argparse
import binascii
import math
import os

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




def analyze(db, proof=False):
	headerbytes = db.read(100)
	header = Header(headerbytes)
	print(header.info(proof))



def main():
	parser = argparse.ArgumentParser(description='Find main colors in a given image.')
	parser.add_argument("database", help="SQLite database file to be examined")
	parser.add_argument('--proof', action='store_true', help="show proofs when possible")
	args = parser.parse_args()
	print(args)
	try:
		db = open(args.database, "rb")
	except OSError:
		print("Try using a database that actually exists.")
	else: 
		print("Real file size: %d\n\n" % os.stat(args.database).st_size)
		analyze(db, args.proof)




if __name__ == "__main__":
	main()






