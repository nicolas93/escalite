#!/usr/bin/env python3
# 2019, Nicolas Schickert, TU Darmstadt



import argparse
import binascii



class Header:
	"""Class containing the information about the sqlite header"""
	headerbytes = b""

	def __init__(self, headerbytes):
		self.headerbytes = headerbytes

	def get_ascii_string(self):
		return self.headerbytes[0:15].decode(), self.headerbytes[0:15]

	def get_page_size(self):
		# TODO to real number
		return self.headerbytes[16:17], self.headerbytes[16:17]

	def get_file_format_write_version(self):
		return self.headerbytes[18], self.headerbytes[18]

	def get_file_format_read_version(self):
		return self.headerbytes[19], self.headerbytes[19]

	def get_file_reserved_bytes(self):
		return self.headerbytes[20], self.headerbytes[20]

	def get_change_count(self):
		return self.headerbytes[24:27], self.headerbytes[24:27]

	def get_db_size(self):
		return self.headerbytes[28:31], self.headerbytes[28,31]

	def get_first_free_page(self):
		return self.headerbytes[32:35], self.headerbytes[32:35]

	def get_count_free_pages(self):
		return self.headerbytes[36:39], self.headerbytes[36:39]

	def get_auto_vacuum_mode(self):
		return self.headerbytes[52:55], self.headerbytes[52:55]

	def get_encoding(self):
		return self.headerbytes[56:59], self.headerbytes[56:59]

	def get_vacuum_mode(self):
		return self.headerbytes[64:68], self.headerbytes[64:68]

	def get_version_number(self):
		return self.headerbytes[96:99], self.headerbytes[96:99]

	def info(self, proof):
		s = ""
		s += "ASCII String: %s\n" % self.get_ascii_string()[0]
		s += "Version: %s\n" % binascii.hexlify(self.get_version_number()[1]).decode()
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
		analyze(db, args.proof)




if __name__ == "__main__":
	main()






