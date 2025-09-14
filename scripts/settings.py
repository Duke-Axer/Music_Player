"""Zapisane sciezki, ustawienia itp"""

import os
import socket

class classproperty(property):
	def __get__(self, obj, cls):
		return self.fget(cls)

class Player():
	"""Informacje o podstawowych i aktualnych parametrach playera"""
	volume = 50
	"""Ustawiona głośność, default 50"""
	name_song = ""
	index_song = 0


class paths():
	libmpv_path_raspberry = "/lib/arm-linux-gnueabihf/libmpv.so"
	libmpv_path_termux = "/data/data/com.termux/files/usr/lib/libmpv.so"
	libmpv_path_local = "libmpv.so"
	
	music_location = "/data/data/com.termux/files/home/storage/music"

class server():
	port = 8000
	_address = None # "192.168.0.106"
	@classmethod
	def get_address(cls):
		"""Zwraca pełny adres z portem"""
		return "http://" + cls.address + ":" + str(cls.port)
	

	@classproperty
	def address(cls):
		"""Adres np: 192.168.0.106"""
		if cls._address is None:
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			try:
				s.connect(("8.8.8.8", 80))
				cls._address = s.getsockname()[0]
			finally:
				s.close()
		return cls._address
