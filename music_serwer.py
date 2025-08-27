import ctypes
import os
import threading
import json
import random
import logging
import time
from flask import Flask, render_template,request, jsonify, Response

LibMPVPlayer = None
MusicLibrary = None


# Konfikuracja i tworzenie HTTP
app = Flask(__name__)
@app.route("/")
def index():
    render_template("index.html")



# Konfiguracja loggera
logging.basicConfig(
    filename='app.log',       # plik do logów
    level=logging.DEBUG,       # loguj wszystko od debug/warning
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# Ładowanie biblioteki libmpv
here = os.path.dirname(__file__)
path_rasp = "/lib/arm-linux-gnueabihf/libmpv.so"
an_p = "/data/data/com.termux/files/usr/lib/libmpv.so"
libmpv_path = os.path.join(here, "libmpv.so")
try:
    libmpv = ctypes.CDLL(an_p)
except:
    libmpv = ctypes.CDLL(libmpv_path)
"""Inna sciezka /data/data/com.termux/files/usr/lib/libmpv.so"""

# Definicje potrzebne do mpv_handle
libmpv.mpv_create.restype = ctypes.c_void_p
libmpv.mpv_initialize.argtypes = [ctypes.c_void_p]
libmpv.mpv_initialize.restype = ctypes.c_int
libmpv.mpv_command.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p)]
libmpv.mpv_command.restype = ctypes.c_int
libmpv.mpv_destroy.argtypes = [ctypes.c_void_p]

class mpv_event(ctypes.Structure):
    _fields_ = [("event_id", ctypes.c_int)]

libmpv.mpv_wait_event.argtypes = [ctypes.c_void_p, ctypes.c_double]
libmpv.mpv_wait_event.restype = ctypes.POINTER(mpv_event)

MPV_EVENT_END_FILE = 4  # Zakończenie pliku

class LibMPVPlayer:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # tutaj możesz inicjalizować atrybuty
            cls._instance.counter = 0
            cls.player = libmpv.mpv_create()
        if cls.player is None:
            logging.error("Nie udało się utworzyć instancji mpv")
            raise RuntimeError("Nie udało się utworzyć instancji mpv")
        if libmpv.mpv_initialize(cls.player) < 0:
            logging.error("Nie udało się zainicjalizować mpv")
            raise RuntimeError("Nie udało się zainicjalizować mpv")
        return cls._instance

    def _cmd(self, *args):
        """Wywołanie polecenia mpv w formie listy stringów"""
        arr = (ctypes.c_char_p * (len(args)+1))()
        arr[:-1] = [s.encode("utf-8") for s in args]
        arr[-1] = None
        libmpv.mpv_command(self.player, arr)

    def play(self, file_path):
        if file_path is None:
            logging.warning("Nie podano pliku do odtworzenia")
            return
        self._cmd("loadfile", file_path, "replace")
    
    def _event_loop(self):
        while self.running:
            event_ptr = libmpv.mpv_wait_event(self.player, 0.1)  # timeout 0.1s
            event = event_ptr.contents
            if event.event_id == MPV_EVENT_END_FILE:
                PlayerCtrl.next()
                self.running = True
                self._event_loop()

    def pause(self):
        logging.debug("LIBMPV - PAUSE")
        self._cmd("set_property", "pause", "yes")

    def resume(self):
        logging.debug("LIBMPV - RESUME")
        self._cmd("set_property", "pause", "no")

    def stop(self):
        logging.debug("LIBMPV - STOP")
        self._cmd("stop")

    def set_volume(self, volume):
        logging.debug("LIBMPV - SET_VOLUME " + str(volume))
        self._cmd("set_property", "volume", str(volume))

    def next(self, file_path):
        logging.debug("LIBMPV - NEXT")
        self.play(file_path)
        
    def close(self):
        logging.debug("LIBMPV - CLOSE")
        libmpv.mpv_destroy(self.player)
        self.player = None



class LibMPVPlayerThreaded(LibMPVPlayer):
    def play_current_threaded(self):
        t = threading.Thread(target=self.play) # , args=(file_path,)
        t.daemon = True  # wątek zakończy się przy zamknięciu programu
        t.start()


class MusicLibrary():
    tags = [] 
    """Tagi piosenek które będą w biblitece, brak oznacza, że wszystkie będą dodane"""
    full_library: dict[str, list[str]] = {}
    """dict[str, list[str]], zawiera wszystkie dostępne piosenki i ich aktualne dane"""
    library = []
    """Zawiera ścieżki do piosenek z albumu"""
    current_index_song = 0
    music_dir = "/data/data/com.termux/files/home/storage/music" 
    # "/data/data/com.termux/files/home/storage/music" "C:/Nekran/Music"
    music_exts = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}
    info_file = "info_music.json"
    _json_file_is_actual = True
    """okresla czy plik json jest aktualny wzgledem listy z muzyka"""
    _instance = None

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
                
    @staticmethod
    def do_library(cls):
        """tworzy liste piosenek, ktore beda odtwarzane"""
        cls.library = []
        for song, tags in cls.full_library.items():
            if not cls.tags or any(tag in cls.tags for tag in tags):
                cls.library.append(song)
        cls.current_index_song = 0
    @staticmethod
    def do_random(cls, yes = True):
        """ustawia randomowa kolejnosc w bibliotece"""
        if yes:
            random.shuffle(cls.library)
            cls.current_index_song = 0
        else:
            cls.do_library()
            
    @staticmethod
    def next(cls):
        cls.current_index_song +=1
        if cls.current_index_song > len(cls.library):
            cls.current_index_song = 0
        path = list(cls.library.keys())[cls.current_index_song]
        return path
    
    @staticmethod
    def before(cls):
        cls.current_index_song -=1
        if cls.current_index_song == -1:
            cls.current_index_song = len(cls.library)
        path = list(cls.library.keys())[cls.current_index_song]
        return path

class PlayerCtrl():
    global LibMPVPlayer, MusicLibrary
    _is_pause = False
    @classmethod
    def pause(cls):
        if _is_pause:
            LibMPVPlayer.resume()
            _is_pause = False
        else:
            LibMPVPlayer.pause()
            _is_pause = True
    @classmethod
    def next(cls):
        LibMPVPlayer.next(MusicLibrary.next())
    @classmethod
    def before(cls):
        LibMPVPlayer.next(MusicLibrary.before())
    @classmethod
    def play(cls):
        LibMPVPlayer.play()


@app.route('/click', methods=['POST'])
def click():
    logging.debug("Obtained Message")
    
    data = request.json
    button_id = data.get('button')
    if button_id == "stop":
        logging.debug("Message - STOP/RESUME")
        PlayerCtrl.pause()
    elif button_id == "next":
        logging.debug("Message - NEXT")
        PlayerCtrl.next()
    elif button_id == "before":
        logging.debug("Message - BEFORE")
        PlayerCtrl.before()

@app.route("/stream")
def stream():
    def event_stream():
        while True:
            time.sleep(1)
            yield f"data: Serwer mówi: {time.ctime()}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")


if __name__ == "__main__":
    logging.debug("START")
    player = LibMPVPlayerThreaded()
    player.play_current_threaded()
    music_lib = MusicLibrary()
    app.run(host="0.0.0.0", port=5000)
    
