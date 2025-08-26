import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest
import ctypes
import threading
import json
import random
import logging
from flask import Flask, render_template,request, jsonify, Response

required_packages = [
    "ctypes",
    "os",
    "json",
    "random",
    "logging",
    "threading",
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
    path = "libmpv.so"
    if not os.path.isfile(path):
        pytest.fail(f"Brak pliku libmpv.so")
    try:
        lib = ctypes.CDLL(path)
    except OSError:
        pytest.fail(f"nie mozna zaladowac libmpv.so")
    
    try:
        from music_serwer import LibMPVPlayerThreaded
        test_file = "tests/test.mp3"
        player = LibMPVPlayerThreaded()
        player.play(test_file)
        time.sleep(3)
        player.stop()
        import threading
        t = threading.Thread(target=play_test)
        t.start()
        t.join()

        print("Test odtworzenia zako?czony.")
    except:
        pytest.fail(f"Nie udało się odtworzyć audio")
