import threading
import time
import datetime
import json

from scripts.settings import paths

class Alarm():
	def __init__(self, name: str, days: list[int], hour: int, minute: int):
		self.name = name
		self.days = days
		self.hour = hour
		self.minute = minute
	def to_dict(self):
		return {
			"name": self.name,
			"days": self.days,
			"hour": self.hour,
			"minute": self.minute
		}
	@classmethod
	def from_dict(cls, data):
		return cls(data["name"], data["days"], data["hour"], data["minute"])

class AlarmManager():
	sould_be_alarm = False
	_alarms: list[Alarm]= []
	next_alarm: Alarm | None = None
	update = True 
	"""Informuje czy należy zaktualizaować informacje o alarmach"""
	
	@classmethod
	def add_alarm(cls, name, days, hour, minute):
		if not AlarmManager._correct_args(name, days, hour, minute):
			return
		alarm_obj = Alarm(name, days, hour, minute)
		cls._alarms.append(alarm_obj)
		cls.update = True
		print("Dodanie alarmu")
	
	@classmethod
	def remove_alarm(cls, name):
		"""Usuwa alarm o danej nazwie z listy"""
		cls._alarms = [alarm for alarm in cls._alarms if alarm.name != name]
		cls.update = True
		print("Usunięcie alarmu")
	
	@classmethod
	def _correct_args(cls, name, days, hour, minute):
		"""Sprawdza czy termin alarmu jest poprawny, oraz czy nazwa się nie powtarza"""
		for alarm in AlarmManager._alarms:
			if name == alarm.name:
				return False

		if not days or not all(1 <= day <= 7 for day in days):
			return False
		elif not  0 <= hour <= 23:
			return False
		elif not  0 <= minute <= 59:
			return False
		else:
			return True
	
	@classmethod
	def save_to_file(cls):
		"""Zapisuje wszystkie alarmy do pliku json"""
		with open(paths.alarms_path, "w", encoding="utf-8") as f:
			json.dump([alarm.to_dict() for alarm in cls._alarms], f, indent=4)
	@classmethod
	def load_from_file(cls):
		"""Odczytuje wszystkie alarmy z pliku json"""
		try:
			with open(paths.alarms_path, "r", encoding="utf-8") as f:
				data = json.load(f)
				cls._alarms = [Alarm.from_dict(item) for item in data]
		except FileNotFoundError:
			cls._alarms = []
	@classmethod
	def return_alarms_as_dict(cls):
		"""Zwraca listę słowników reprezentujących wszystkie alarmy."""
		return [alarm.to_dict() for alarm in cls._alarms]
			
	@staticmethod
	def get_next_alarm_time(alarm: Alarm):
		now = datetime.datetime.now()
		weekday_now = now.isoweekday()  # 1 = poniedziałek, 7 = niedziela
        
        # Znajdź wszystkie dni z listy, które są dzisiaj lub później
		potential_days = []
		for day in alarm.days:
            # Oblicz, ile dni do przodu jest ten dzień (0-6)
			days_ahead = (day - weekday_now) % 7
			potential_days.append(days_ahead)
        
		min_days_ahead = float('inf')
		target_day = -1
        
        # Iteracja przez dni, które zostały skonfigurowane dla alarmu
		for day in alarm.days:
			days_to_add = (day - weekday_now) % 7
            
            # Tworzymy czas alarmu na bieżący tydzień (lub następny, jeśli days_to_add > 0)
			alarm_datetime = datetime.datetime(now.year, now.month, now.day, alarm.hour, alarm.minute)
			alarm_datetime += datetime.timedelta(days=days_to_add)

            # Specjalna obsługa, jeśli jest to DZISIAJ (days_to_add == 0)
			if days_to_add == 0 and alarm_datetime <= now:
                # Jeśli dziś, ale czas już minął, dodajemy 7 dni
				days_to_add = 7
				alarm_datetime = datetime.datetime(now.year, now.month, now.day, alarm.hour, alarm.minute)
				alarm_datetime += datetime.timedelta(days=days_to_add)
            
            # Najmniejsza różnica
			if days_to_add < min_days_ahead:
				min_days_ahead = days_to_add
				target_day = day
				next_alarm_time = alarm_datetime
        
		return next_alarm_time
	@classmethod
	def next_alarm(cls):
		if not cls._alarms:
			return None
		return min(cls._alarms, key=cls.get_next_alarm_time)


def alarm_thread():
	sleep_seconds = float("inf")
	while True:
		if AlarmManager.update:
			if not AlarmManager._alarms:
				time.sleep(60)
				continue
			print("Alarmy:",AlarmManager._alarms)
			next_alarm = AlarmManager.next_alarm()
		if sleep_seconds > 60:
			time.sleep(10)
			alarm_time = AlarmManager.get_next_alarm_time(next_alarm)
			sleep_seconds = (alarm_time - datetime.datetime.now()).total_seconds()
			AlarmManager.update = False

			print(f"Następny alarm {next_alarm.name} za: {sleep_seconds}s")
		else:
			print("odliczanie")
			time.sleep(sleep_seconds)
			AlarmManager.sould_be_alarm = True
			AlarmManager.update = True

def start_alarm_shread():
	thread = threading.Thread(target=alarm_thread, daemon=True)
	thread.start()