"""Klasa MusicLibrary"""

import os
import json
import random

from scripts.settings import paths, Player

class MusicLibrary():
    """Zarządza biblioteką muzyczną"""
    tags = [] 
    """Tagi piosenek które będą w biblitece, brak oznacza, że wszystkie będą dodane"""
    full_library: dict[str, list[str]] = {}
    """dict[str, list[str]], zawiera wszystkie dostępne piosenki i ich aktualne dane"""
    library = []
    """Zawiera listę piosenek z albumu"""
    music_dir = paths.music_location
    music_exts = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}
    info_file = "info_music.json"
    _json_file_is_actual = True
    """okresla czy plik json jest aktualny wzgledem listy z muzyka"""
    _instance = None
    is_rnd_flag = False
    """Okresla czy piosenki sa ulozone randomowo"""
    is_actual_library = True
    """Okresla czy biblioteka jest aktualna"""

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.current_track = None
            cls.read_dir_library()
            cls.do_library()
        return cls._instance
        
    @classmethod
    def _find_music_files(cls):
        """zapisuje do pliku json wszystkie nowe pliki audio"""
        _new_file_exist = False
        for root, dirs, files in os.walk(cls.music_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in cls.music_exts:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, cls.music_dir).replace("\\", "/")
                    if rel_path not in cls.full_library:
                        _new_file_exist = True
                        cls.full_library[rel_path] = []
        if _new_file_exist:
            cls._create_info_file()
        

    @classmethod
    def _create_info_file(cls):
        """tworzy plik json, 
        zapisuje slownik z muzyka do pliku json"""
        with open(cls.info_file, "w", encoding="utf-8") as f:
            json.dump(cls.full_library, f, ensure_ascii=False, indent=4)
            print(f"Zapisano {len(cls.full_library)} plików muzycznych do '{cls.info_file}'")
        cls._json_file_is_actual = True
        
        
    @classmethod
    def read_dir_library(cls):
        """Odczytuje plik JSON z informacjami o utworach i nadpisuje słownik."""
        if os.path.exists(cls.info_file):
            with open(cls.info_file, "r", encoding="utf-8") as f:
                cls.full_library = json.load(f)
        else:
            cls.full_library = {}
            cls._create_info_file()
        cls._json_file_is_actual = True
    @classmethod
    def change_music_tags(cls, name_audio, tag, add = True):
        """dodaje/usuwa tag do utworu, nie dodaje duplikatow"""
        if name_audio in cls.full_library:
            if tag not in cls.full_library[name_audio] and add:
                cls.full_library[name_audio].append(tag)
            elif tag in cls.full_library[name_audio] and not add:
                cls.full_library[name_audio].remove(tag)
        cls._json_file_is_actual = False
                
    @classmethod
    def do_library(cls):
        """tworzy liste piosenek, ktore beda odtwarzane"""
        cls.library = []
        for song, tags in cls.full_library.items():
            if not cls.tags or any(tag in cls.tags for tag in tags):
                cls.library.append(song)
        if MusicLibrary.is_rnd_flag:
            random.shuffle(cls.library)
        Player.index_song = 0
        Player.index_song = 0
        cls.is_actual_library = False
    @classmethod
    def do_random(cls, yes = True):
        """ustawia randomowa kolejnosc w bibliotece"""
        MusicLibrary.is_rnd_flag = yes
        cls.do_library()
            
    @classmethod
    def next(cls):
        """Zwiększa aktualny indeks piosenki o +1, po ostatniej piosence w albumie cofa się do 0.
        Jeśli piosenki w albumie są ustawione randomowo, to po ostatniej piosence losuje ponownie"""
        Player.index_song +=1
        if Player.index_song >= len(cls.library):
            Player.index_song = 0
            if MusicLibrary.is_rnd_flag:
                MusicLibrary.do_random(True)
        path = cls.library[Player.index_song]
        return os.path.join(cls.music_dir, path)
    
    @classmethod
    def before(cls):
        """Ustawia indeks piosneki o 1 mniejszy, bo nie ma zapisanej historii odtwarzania"""
        Player.index_song -=1
        if Player.index_song == -1:
            Player.index_song = len(cls.library) -1
        path = cls.library[Player.index_song]
        return os.path.join(cls.music_dir, path)

    @classmethod
    def play(cls, index: int = Player.index_song):
        """Zwraca pełną ścieżkę, potrzebną do odtworzenia pliku audio
        Args:
            index (int): Numer audio w albumie, domyślnie pobiera z Player.index_song
        Returns:
            str: Pełna ścieżka do pliku audio: cls.music_dir + Player.name_song"""
        Player.name_song = cls.library[index]
        return os.path.join(cls.music_dir, Player.name_song)
        
    @classmethod
    def get_index_song(cls, song_name: str = Player.name_song):
        """Zwraca numer piosenki w albumie.  
        Ta sama piosenka będzie miała różne indeksy, jeśli w albumie piosenki są ustawione losowo.
        Args:
            song_name (str): nazwa piosenki, default Player.name_song
        Returns:
        int: indeks piosenki o danej nazwie, jeśli nie istnieje to zwraca 0"""
        print(song_name)

        if song_name in cls.library:
            return cls.library.index(song_name)
        else:
            return 0