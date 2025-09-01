"""Zapisane sciezki itp"""

import os

class paths():
	libmpv_path_raspberry = "/lib/arm-linux-gnueabihf/libmpv.so"
	libmpv_path_termux = "/data/data/com.termux/files/usr/lib/libmpv.so"
	libmpv_path_local = "libmpv.so"
	
	music_location = "/data/data/com.termux/files/home/storage/music"

class server():
	port = 8000
	address = "192.168.0.104"
	@classmethod
	def get_address(cls):
		return "http://" + cls.address + ":" + str(cls.port) + "/click"
