import ctypes
import os
import threading
import json
import random
import logging
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
libmpv = ctypes.CDLL("libmpv.so")
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
        if self.player is None:
            logging.error("Nie udało się utworzyć instancji mpv")
            raise RuntimeError("Nie udało się utworzyć instancji mpv")
        if libmpv.mpv_initialize(self.player) < 0:
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
        self._cmd("loadfile", file_path, "replace")
    
    def _event_loop(self):
        while self.running:
            event_ptr = libmpv.mpv_wait_event(self.player, 0.1)  # timeout 0.1s
            event = event_ptr.contents
            if event.event_id == MPV_EVENT_END_FILE:
                self.next()
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
        t = threading.Thread(target=self.play)
        t.daemon = True  # wątek zakończy się przy zamknięciu programu
        t.start()


class MusicLibrary():
    tags = [] 
    """Tagi piosenek które będą w biblitece, brak oznacza, że wszystkie będą dodane"""
    full_library: dict[str, list[str]] = {}
    """dict[str, list[str]], zawiera wszystkie dostępne piosenki"""
    library = []
    """Zawiera ścieżki do piosenek z albumu"""
    current_index_song = 0
    music_dir = "/data/data/com.termux/files/home/storage/music" 
    # "/data/data/com.termux/files/home/storage/music" "C:/Nekran/Music"
    muzyka_exts = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}
    info_file = "info_music.json"
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.current_track = None
        return cls._instance

    def _create_info_file(self):
        music_files = {}
        for root, dirs, files in os.walk(music_library.music_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in music_library.music_exts:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, music_library.music_dir).replace("\\", "/")
                    music_files[rel_path] = []

        # Zapis do JSON
        with open(music_library.info_file, "w", encoding="utf-8") as f:
            json.dump(music_files, f, ensure_ascii=False, indent=4)
            print(f"Zapisano {len(music_files)} plików muzycznych do '{music_library.info_file}'")

    def read_dir_library(self):
        """Odczytuje plik JSON z informacjami o utworach i zwraca słownik."""
        if not os.path.exists(music_library.info_file):
            print(f"Plik '{MusicLibrary.info_file}' nie istnieje.")
            MusicLibrary.full_library = {}
            return

        with open(music_library.info_file, "r", encoding="utf-8") as f:
            MusicLibrary.full_library = json.load(f)

    def change_music_tags(self):
        pass

    def do_library(self):
        MusicLibrary.library = []
        for song, tags in MusicLibrary.full_library.items():
            if tag in tags:
                MusicLibrary.library.append(song)
        
    def do_random(self, yes = True):
        if yes:
            random.shuffle(music_library.library)
            MusicLibrary.current_index_song = 0
        else:
            music_lib.do_library()
    def next():
        MusicLibrary.current_index_song +=1
        if MusicLibrary.current_index_song > len(MusicLibrary.library):
            MusicLibrary.current_index_song = 0
        path = list(MusicLibrary.library.keys())[MusicLibrary.current_index_song]
        return path
    def before():
        MusicLibrary.current_index_song -=1
        if MusicLibrary.current_index_song == -1:
            MusicLibrary.current_index_song = len(MusicLibrary.library)
        path = list(MusicLibrary.library.keys())[MusicLibrary.current_index_song]
        return path

class PlayerCtrl():
    global LibMPVPlayer, MusicLibrary
    _isPause = False
    def pause():
        if _isPause:
            LibMPVPlayer.resume()
            _isPause = False
        else:
            LibMPVPlayer.pause()
            _isPause = True
    def next():
        LibMPVPlayer.next(MusicLibrary.next())
    def before():
        LibMPVPlayer.next(MusicLibrary.before())
    def play():
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

def test():
    
    def libmpv():
        global LibMPVPlayer
        song_path_test = ""
        LibMPVPlayer.play(song_path_test)
        time.sleep(3)
        LibMPVPlayer.stop()
    

if __name__ == "__main__":
    logging.debug("START")
    player = LibMPVPlayer()
    player.play_current_threaded()
    music_lib = MusicLibrary()
    app.run(host="0.0.0.0", port=5000)
    
