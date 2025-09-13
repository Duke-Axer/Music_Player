"""Obsluga libmpv"""
import os
import ctypes
import logging
logger = logging.getLogger(__name__)

from scripts.settings import paths

MPV_END_FILE_REASON_EOF = 0  # Normalne zakończenie
MPV_END_FILE_REASON_STOP = 2  # Zatrzymane przez użytkownika
MPV_END_FILE_REASON_QUIT = 3  # Zakończenie aplikacji

try:
    libmpv = ctypes.CDLL(paths.libmpv_path_termux)
except Exception as e:
    try:
        libmpv = ctypes.CDLL(paths.libmpv_path_local)
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
    _fields_ = [
        ("event_id", ctypes.c_int),
        ("error", ctypes.c_int),
        ("reply_userdata", ctypes.c_ulonglong),  # w C to uint64_t
        ("data", ctypes.c_void_p),
    ]

if libmpv:
    libmpv.mpv_wait_event.argtypes = [ctypes.c_void_p, ctypes.c_double]
    libmpv.mpv_wait_event.restype = ctypes.POINTER(mpv_event)

    libmpv.mpv_event_name.argtypes = [ctypes.c_int]
    libmpv.mpv_event_name.restype = ctypes.c_char_p

MPV_EVENT_END_FILE = 4  # Zakończenie pliku

class LibMPVPlayer:
    _instance = None
    _initialized = False
    player = None 
    running = False
    counter = 0
    on_song_end = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            
            # Tworzenie instancji mpv tylko jeśli biblioteka jest dostępna
            if libmpv:
                try:
                    cls.player = libmpv.mpv_create()  
                    if cls.player:
                        ret = libmpv.mpv_initialize(cls.player)
                        if ret < 0:
                            logging.error(f"Nie udało się zainicjalizować mpv, kod: {ret}")
                            cls.player = None
                        else:
                            cls._initialized = True
                            logging.info("MPV zainicjalizowany pomyślnie")
                    else:
                        logging.error("Nie udało się utworzyć instancji mpv")
                except Exception as e:
                    logging.exception("Błąd podczas inicjalizacji mpv: %s", e)
                    cls.player = None
            else:
                logging.error("Biblioteka libmpv nie jest dostępna")
        
        return cls._instance

    @classmethod
    def _cmd(cls, *args):
        """Wywołanie polecenia mpv"""
        if not cls.player:
            logging.warning("Player nie jest zainicjalizowany")
            return
        
        try:
            arr = (ctypes.c_char_p * (len(args) + 1))()
            arr[:-1] = [s.encode("utf-8") for s in args]
            arr[-1] = None
            libmpv.mpv_command(cls.player, arr)
        except Exception as e:
            logging.error(f"Błąd podczas wykonywania polecenia: {e}")

    @classmethod
    def play(cls, file_path):
        if not cls.player:
            logging.warning("Player nie jest zainicjalizowany")
            return
            
        if file_path is None:
            logging.warning("Nie podano pliku do odtworzenia")
            return
            
        if not os.path.exists(file_path):
            logging.warning(f"Plik nie istnieje: {file_path}")
            return
            
        cls._cmd("loadfile", file_path, "replace")
    
    @classmethod
    def _event_loop(cls):
        if not cls.player:
            return
            
        cls.running = True
        while cls.running:
            try:
                event_ptr = libmpv.mpv_wait_event(cls.player, 0.1)
                if event_ptr:
                    event = event_ptr.contents
                    ev_name = libmpv.mpv_event_name(event.event_id).decode()
                    print(f"EVENT: {event.event_id} ({ev_name})")
                    if event.event_id == MPV_EVENT_END_FILE:
                        # Koniec odtwarzania pliku
                        print("Koniec pliku")
                        if event.data:
                            # Konwertuj data na strukturę end_file_reason
                            reason = ctypes.cast(event.data, ctypes.POINTER(ctypes.c_int)).contents.value
                            print(f"Koniec pliku, przyczyna: {reason}")
                        if reason == 0:  # MPV_END_FILE_REASON_EOF
                                logging.info("Koniec pliku (normalne zakończenie)")
                                if cls.on_song_end:
                                    cls.on_song_end()
                        else:
                            logging.info("Koniec pliku (brak danych o przyczynie)")
                            if cls.on_song_end:
                                cls.on_song_end()
            except Exception as e:
                logging.error(f"Błąd w pętli zdarzeń: {e}")
                break

    @classmethod
    def pause(cls):
        logging.debug("LIBMPV - PAUSE")
        cls._cmd("set", "pause", "yes")

    @classmethod
    def resume(cls):
        logging.debug("LIBMPV - RESUME")
        cls._cmd("set", "pause", "no")

    @classmethod
    def stop(cls):
        logging.debug("LIBMPV - STOP")
        cls._cmd("stop")

    @classmethod
    def set_volume(cls, volume):
        logging.debug("LIBMPV - SET_VOLUME " + str(volume))
        cls._cmd("set", "volume", str(volume))

    @classmethod
    def next(cls, file_path):
        logging.debug("LIBMPV - NEXT")
        cls.play(file_path)
        
    
    @classmethod
    def close(cls):
        logging.debug("LIBMPV - CLOSE")
        if cls.player:
            try:
                libmpv.mpv_destroy(cls.player)
            except Exception as e:
                logging.error(f"Błąd podczas zamykania player: {e}")
            finally:
                cls.player = None
