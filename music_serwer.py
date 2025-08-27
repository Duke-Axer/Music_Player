import ctypes
import os
import threading
import json
import random
import logging
import time
from flask import Flask, render_template,request, jsonify, Response
from flask_cors import CORS

LibMPVPlayer = None
MusicLibrary = None


# Konfikuracja i tworzenie HTTP
app = Flask(__name__)
CORS(app)
@app.route("/")
def index():
    return render_template("index.html")



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
except Exception as e:
    try:
        libmpv = ctypes.CDLL(libmpv_path)
    except Exception as e:
        logging.error(f"Nie udało się załadować libmpv: {e}")
        libmpv = None

# Definicje potrzebne do mpv_handle
if libmpv:
    libmpv.mpv_create.restype = ctypes.c_void_p
    libmpv.mpv_initialize.argtypes = [ctypes.c_void_p]
    libmpv.mpv_initialize.restype = ctypes.c_int
    libmpv.mpv_command.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p)]
    libmpv.mpv_command.restype = ctypes.c_int
    libmpv.mpv_destroy.argtypes = [ctypes.c_void_p]

class mpv_event(ctypes.Structure):
    _fields_ = [("event_id", ctypes.c_int)]

if libmpv:
    libmpv.mpv_wait_event.argtypes = [ctypes.c_void_p, ctypes.c_double]
    libmpv.mpv_wait_event.restype = ctypes.POINTER(mpv_event)

MPV_EVENT_END_FILE = 4  # Zakończenie pliku

class LibMPVPlayer:
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Inicjalizacja atrybutów
            cls._instance.player = None
            cls._instance.running = False
            cls._instance.counter = 0
            
            # Tworzenie instancji mpv tylko jeśli biblioteka jest dostępna
            if libmpv:
                try:
                    cls._instance.player = libmpv.mpv_create()
                    if cls._instance.player:
                        ret = libmpv.mpv_initialize(cls._instance.player)
                        if ret < 0:
                            logging.error(f"Nie udało się zainicjalizować mpv, kod: {ret}")
                            cls._instance.player = None
                        else:
                            cls._initialized = True
                            logging.info("MPV zainicjalizowany pomyślnie")
                    else:
                        logging.error("Nie udało się utworzyć instancji mpv")
                except Exception as e:
                    logging.exception("Błąd podczas inicjalizacji mpv: %s", e)
                    cls._instance.player = None
            else:
                logging.error("Biblioteka libmpv nie jest dostępna")
        
        return cls._instance

    def _cmd(self, *args):
        """Wywołanie polecenia mpv"""
        if not self.player:
            logging.warning("Player nie jest zainicjalizowany")
            return
        
        try:
            arr = (ctypes.c_char_p * (len(args) + 1))()
            arr[:-1] = [s.encode("utf-8") for s in args]
            arr[-1] = None
            libmpv.mpv_command(self.player, arr)
        except Exception as e:
            logging.error(f"Błąd podczas wykonywania polecenia: {e}")

    def play(self, file_path):
        if not self.player:
            logging.warning("Player nie jest zainicjalizowany")
            return
            
        if file_path is None:
            logging.warning("Nie podano pliku do odtworzenia")
            return
            
        if not os.path.exists(file_path):
            logging.warning(f"Plik nie istnieje: {file_path}")
            return
            
        self._cmd("loadfile", file_path, "replace")
    
    def _event_loop(self):
        if not self.player:
            return
            
        self.running = True
        while self.running:
            try:
                event_ptr = libmpv.mpv_wait_event(self.player, 0.1)
                if event_ptr:
                    event = event_ptr.contents
                    if event.event_id == MPV_EVENT_END_FILE:
                        # Tutaj możesz dodać logikę dla końca pliku
                        logging.info("Koniec pliku")
            except Exception as e:
                logging.error(f"Błąd w pętli zdarzeń: {e}")
                break

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
        self._cmd("set", "volume", str(volume))

    def next(self, file_path):
        logging.debug("LIBMPV - NEXT")
        self.play(file_path)
        
    def close(self):
        logging.debug("LIBMPV - CLOSE")
        if self.player:
            try:
                libmpv.mpv_destroy(self.player)
            except Exception as e:
                logging.error(f"Błąd podczas zamykania player: {e}")
            finally:
                self.player = None



class LibMPVPlayerThreaded(LibMPVPlayer):
    def play_current_threaded(self, file_path=None):
        if not self.player:
            logging.warning("Player nie jest zainicjalizowany")
            return
            
        t = threading.Thread(target=self.play, args=(file_path,))
        t.daemon = True
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
                
    @classmethod
    def do_library(cls):
        """tworzy liste piosenek, ktore beda odtwarzane"""
        cls.library = []
        for song, tags in cls.full_library.items():
            if not cls.tags or any(tag in cls.tags for tag in tags):
                cls.library.append(song)
        cls.current_index_song = 0
    @classmethod
    def do_random(cls, yes = True):
        """ustawia randomowa kolejnosc w bibliotece"""
        if yes:
            random.shuffle(cls.library)
            cls.current_index_song = 0
        else:
            cls.do_library()
            
    @classmethod
    def next(cls):
        cls.current_index_song +=1
        if cls.current_index_song > len(cls.library):
            cls.current_index_song = 0
        path = cls.library[cls.current_index_song]
        return os.path.join(cls.music_dir, path)
    
    @classmethod
    def before(cls):
        cls.current_index_song -=1
        if cls.current_index_song == -1:
            cls.current_index_song = len(cls.library)
        path = cls.library[cls.current_index_song]
        return os.path.join(cls.music_dir, path)

class PlayerCtrl():
    global LibMPVPlayer, MusicLibrary
    _is_pause = False
    @classmethod
    def pause(cls):
        if cls._is_pause:
            LibMPVPlayer.resume()
            cls._is_pause = False
        else:
            LibMPVPlayer.pause()
            cls._is_pause = True
    @classmethod
    def next(cls):
        LibMPVPlayer.next(MusicLibrary.next())
    @classmethod
    def before(cls):
        LibMPVPlayer.next(MusicLibrary.before())
    @classmethod
    def play(cls):
        LibMPVPlayer.play()

@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/click', methods=['GET', 'POST'])  # ← Dodaj GET
def click():
    print("=== /click endpoint called ===")
    
    if request.method == 'GET':
        # Dla testowania GET
        button_id = request.args.get('button')
        print(f"GET request with button: {button_id}")
        return jsonify({"status": "success", "button": button_id, "method": "GET"})
    logging.debug("Obtained Message")
    try:
        data = request.get_json()
        print(f"Received data: {data}")
        if not data:
            return jsonify({"error": "No JSON data"}), 400
            
        button_id = data.get('button')
        
        if button_id == "test":  # ← Dodaj tę obsługę
            print("✅ TEST button pressed - This message appears in Termux!")
            return jsonify({"status": "success", "message": "Test received in terminal"})
            
        elif button_id == "stop":
            logging.debug("Message - STOP/RESUME")
            PlayerCtrl.pause()
        elif button_id == "next":
            logging.debug("Message - NEXT")
            PlayerCtrl.next()
        elif button_id == "before":
            logging.debug("Message - BEFORE")
            PlayerCtrl.before()
        else:
            logging.warning(f"Unknown button: {button_id}")
            return jsonify({"error": "Unknown button"}), 400
            
        return jsonify({"status": "success", "button": button_id})
        
    except Exception as e:
        logging.error(f"Error in click handler: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/stream")
def stream():
    def event_stream():
        while True:
            time.sleep(1)
            yield f"data: Serwer mówi: {time.ctime()}\n\n"
    
    response = Response(event_stream(), mimetype="text/event-stream")
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Cache-Control', 'no-cache')
    return response

@app.route('/test')
def test_endpoint():
    return jsonify({"status": "ok", "message": "Server is working!"})

@app.route('/test-post', methods=['POST'])
def test_post():
    data = request.json
    return jsonify({"status": "received", "data": data})

def run_flask_server():
    """Uruchamia serwer Flask w osobnym wątku"""
    print("Starting Flask server on http://0.0.0.0:8000")
    try:
        app.run(host="0.0.0.0", port=8000, debug=True, use_reloader=False, threaded=True)
    except Exception as e:
        print(f"Flask server error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logging.debug("START")
    # player = LibMPVPlayerThreaded()
    # if player.player:
    #     print("Creating player")
    #     player.play_current_threaded()
    # else:
    #     logging.warning("player nie został zainicjowany")
    #     print("player nie został zainicjowany")
    print("Creating music library")
    music_lib = MusicLibrary()
    print("Starting Flask server...")
    flask_thread = threading.Thread(target=run_flask_server)
    flask_thread.daemon = True  # Wątek zakończy się gdy główny program się zakończy
    flask_thread.start()
    time.sleep(3)  # ← Dodaj 3 sekundy opóźnienia
    print("Server should be ready now at http://127.0.0.1:8000")
    while True:
            time.sleep(1)
