import pytest

import ctypes
import os
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
def test_import_flask(flask_p)
    try:
        mod = __import__("flask", fromlist=[elem])
        getattr(mod, flask_p)
    except (ImportError, AttributeError):
        pytest.fail(f"Brak zainstalowanej biblioteki flask: {flask_p}")

