import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest
from flask import Flask, render_template,request, jsonify, Response
    
required_packages = [
    "ctypes",
    "os",
    "json",
    "random",
    "logging",
    "threading",
    "json",
]

@pytest.mark.parametrize("package", required_packages)
def test_import(package):
    try:
        __import__(package)
    except ImportError:
        pytest.fail(f"Brak zainstalowanej biblioteki: {package}")
        
flask_elements = ["Flask", "render_template", "request", "jsonify", "Response"]


@pytest.mark.parametrize("flask_p", flask_elements)
def test_import_flask(flask_p):
    try:
        mod = __import__("flask", fromlist=[flask_p])
        getattr(mod, flask_p)
    except (ImportError, AttributeError):
        pytest.fail(f"Brak zainstalowanej biblioteki flask: {flask_p}")

def test_libmpv():
    import ctypes
    from music_serwer import LibMPVPlayerThreaded
    import time
    path = "libmpv.so"
    if not os.path.isfile(path):
        pytest.fail(f"Brak pliku libmpv.so")
    try:
        lib = ctypes.CDLL(path)
    except OSError:
        pytest.fail(f"nie mozna zaladowac libmpv.so")
    
    try:
        test_file = "tests/test.mp3"
        player = LibMPVPlayerThreaded()
        player.play(test_file)
        time.sleep(3)
        player.stop()
        try:
            # testowanie zmiany glosnosci
            player = LibMPVPlayerThreaded()
            player.play(test_file)
            player.set_volume(20)
            time.sleep(1)
            player.set_volume(100)
            time.sleep(1)
            player.set_volume(20)
            time.sleep(1)
            player.set_volume(100)
            player.stop()
        except:
            pytest.fail(f"Nie udało się zmienić głośności")
    except:
        pytest.fail(f"Nie udało się odtworzyć audio")

def test_music_dir_exists():
    from music_serwer import MusicLibrary
    if not os.path.isdir(MusicLibrary.music_dir):
        pytest.fail(f"niepoprawna sciezka z muzyka")
    
    _music_file_exist = False
    for root, dirs, files in os.walk(MusicLibrary.music_dir):
        if _music_file_exist:
            break
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in MusicLibrary.music_exts:
                _music_file_exist = True
                break
    else:
        pytest.fail(f"sciezka z piosenkami nie zawiera muzyki")

def test_MusicLibrary():
    import json
    from music_serwer import MusicLibrary
    MusicLibrary.music_dir = "tests"
    MusicLibrary.info_file = "tests/info_music.json"
    if os.path.exists(MusicLibrary.info_file):
        os.remove(MusicLibrary.info_file)
    try:
        MusicLibrary._find_music_files()
    except:
        pytest.fail(f"Nie udalo sie wykonac utworzenia pliku: " + MusicLibrary.info_file)
    else:
        try:    
            MusicLibrary.read_dir_library()
        except:
            pytest.fail (f"Nie udalo sie wykonac odczytania pliku: " + MusicLibrary.info_file)
        else:
            if not MusicLibrary.full_library == {"test.mp3": []}:
                pytest.fail(f"zly format pliku json:" + str(MusicLibrary.full_library))
    if os.path.exists(MusicLibrary.info_file):
        os.remove(MusicLibrary.info_file)
    with open(MusicLibrary.info_file, "w", encoding="utf-8") as f:
        json.dump({"test.mp3": []}, f)
    try:
        MusicLibrary.change_music_tags(name_audio = "test.mp3", tag = "test_tag", add = True)
    except:
        pytest.fail(f"nie mozna dodac tagu")
        
    MusicLibrary.change_music_tags("test.mp3", "test_tag", add = True)
    if not MusicLibrary.full_library == {"test.mp3": ["test_tag"]}:
        pytest.fail(f"tag nie zostal dodany:" + str(MusicLibrary.full_library))
    MusicLibrary._create_info_file()
    MusicLibrary.full_library = {}
    MusicLibrary.read_dir_library()
    if not MusicLibrary.full_library == {"test.mp3": ["test_tag"]}:
        pytest.fail(f"tag nie zostal zapisany do pliku json:" + str(MusicLibrary.full_library))
    
    
        
                
        
    
    
    
