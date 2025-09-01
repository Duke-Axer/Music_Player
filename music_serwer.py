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
from scripts.music_library import MusicLibrary


song_update_queue = Queue()


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
    is_rnd = False
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
            notify_volume(volume)
        
        elif button_id == "rnd":
            is_rnd = not is_rnd
            print(f"Zmiana trybu randomowosci")
            MusicLibrary.do_random(is_rnd)
            song_update_queue(is_rnd)
            
        else:
            print(f"❌ Unknown button: {button_id}")
            return jsonify({"error": "Unknown button"}), 400
            
        return jsonify({"status": "success", "button": button_id})
        
    except Exception as e:
        print(f"❌ ERROR in click handler: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
        
def notify_current_song(song_path):
    """wysyla informacje o aktualnej piosence"""
    song_name = os.path.basename(song_path)
    song_update_queue.put({"type": "song", "value": song_name})

def notify_volume(volume):
    """wysyla informacje o glosnosci"""
    song_update_queue.put({"type": "volume", "value": volume})

def notify_rnd_flag(is_rnd):
    """wysyla informacje, czy playlista jest ustawiona randomowo"""
    song_update_queue.put({"type": "random", "value": is_rnd})

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
    try:
        app.run(host="0.0.0.0", port=8000, debug=True, use_reloader=False, threaded=True)
    except Exception as e:
        logging.warning(f"Blad uruchomienia serwera")
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
            print(f"Piosenka : {first_song_path}")
            LibMPVPlayer.play(first_song_path)
    else:
        logging.warning("Player nie został zainicjowany")
        print("player nie został zainicjowany")
    
    print("Start serwera")
    flask_thread = threading.Thread(target=run_flask_server)
    flask_thread.daemon = True
    flask_thread.start()
    
    time.sleep(3)
    print("Serwer dziala http://127.0.0.1:8000")
    
    while True:
        time.sleep(1)
