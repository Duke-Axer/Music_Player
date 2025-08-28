import ctypes
import os
import threading
import json
import random
import logging
import time
from flask import Flask, render_template,request, jsonify, Response
from flask_cors import CORS
from queue import Queue

LibMPVPlayer = None
MusicLibrary = None

from scripts.settings import paths, server
from scripts.lib_mpv_player import *


song_update_queue = Queue()

def notify_current_song(song_path):
    song_name = os.path.basename(song_path)
    song_update_queue.put(song_name)

# Konfikuracja i tworzenie HTTP
app = Flask(__name__)
CORS(app)
@app.route("/")
def index():
    return render_template("index.html", api_url= server.get_address())


# Konfiguracja loggera
logging.basicConfig(
    filename='app.log',       # plik do logów
    level=logging.DEBUG,       # loguj wszystko od debug/warning
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)


class LibMPVPlayerThreaded(LibMPVPlayer):
    @classmethod
    def play_current_threaded(cls, file_path=None):
        if not cls.player:
            logging.warning("Player nie jest zainicjalizowany")
            return
            
        t = threading.Thread(target=cls.play, args=(file_path,))
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
    music_dir = paths.music_location
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
            cls.current_index_song = len(cls.library) -1
        path = cls.library[cls.current_index_song]
        return os.path.join(cls.music_dir, path)

class PlayerCtrl():
    global LibMPVPlayer, MusicLibrary
    _is_pause = False
    @classmethod
    def pause(cls):
        if LibMPVPlayer.player:
            if cls._is_pause:
                LibMPVPlayer.resume()
                cls._is_pause = False
            else:
                LibMPVPlayer.pause()
                cls._is_pause = True
        else:
            logging.warning("Player not initialized!")
    @classmethod
    def next(cls):
        path = MusicLibrary.next()
        LibMPVPlayer.next(path)
        notify_current_song(path)
    @classmethod
    def before(cls):
        path = MusicLibrary.before()
        LibMPVPlayer.next(path)
        notify_current_song(path)
    @classmethod
    def play(cls):
        LibMPVPlayer.play()
        if MusicLibrary.library:
            notify_current_song(os.path.join(MusicLibrary.music_dir, 
            MusicLibrary.library[MusicLibrary.current_index_song]))

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

@app.route('/click', methods=['GET', 'POST'])
def click():
    print("=== /click endpoint called ===")
    
    try:
        data = request.get_json()
        print(f"Received data: {data}")
        
        if not data:
            return jsonify({"error": "No JSON data"}), 400
            
        button_id = data.get('button')
        
        if button_id == "test":
            print("✅ TEST button pressed")
            return jsonify({"status": "success", "message": "Test received in terminal"})
            
        elif button_id == "stop":
            print("🔄 STOP/RESUME command")
            PlayerCtrl.pause()
            
        elif button_id == "next":
            print("⏭️ NEXT command")
            PlayerCtrl.next()
            
        elif button_id == "before":
            print("⏮️ BEFORE command")
            PlayerCtrl.before()
            
        elif button_id == "volume":
            volume = data.get('volume', 50)
            print(f"🔊 VOLUME change: {volume}%")
            LibMPVPlayer.set_volume(volume)
            
        else:
            print(f"❌ Unknown button: {button_id}")
            return jsonify({"error": "Unknown button"}), 400
            
        return jsonify({"status": "success", "button": button_id})
        
    except Exception as e:
        print(f"❌ ERROR in click handler: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
@app.route("/stream")
def stream():
    def event_stream():
        while True:
            song_name = song_update_queue.get()  # czeka na nową wiadomość
            yield f"data: {song_name}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

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
    
    # Inicjalizuj player
    player = LibMPVPlayer()
    
    if LibMPVPlayer.player:
        print("Player created successfully")
        # Odtwórz pierwszą piosenkę jeśli biblioteka ma utwory
        music_lib = MusicLibrary()
        music_lib.read_dir_library()
        music_lib._find_music_files()
        print(len(music_lib.full_library))
        music_lib.do_library()
        print(len(music_lib.library))


        if music_lib.library:
            first_song_path = os.path.join(music_lib.music_dir, music_lib.library[0])
            print(f"Playing first song: {first_song_path}")
            LibMPVPlayer.play(first_song_path)
    else:
        logging.warning("Player nie został zainicjowany")
        print("player nie został zainicjowany")
    
    print("Starting Flask server...")
    flask_thread = threading.Thread(target=run_flask_server)
    flask_thread.daemon = True
    flask_thread.start()
    
    time.sleep(3)
    print("Server should be ready now at http://127.0.0.1:8000")
    
    while True:
        time.sleep(1)
