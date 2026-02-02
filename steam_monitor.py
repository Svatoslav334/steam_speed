import winreg
import time
import threading
import re
from pathlib import Path


#Поиск Steam
def get_steam_path():
	key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
	path, _ = winreg.QueryValueEx(key, "SteamPath")
	return Path(path)


#Библиотеки 

def get_libraries(steam_path):
	vdf = steam_path / "steamapps" / "libraryfolders.vdf"
	libs = []
	with open(vdf, 'r', encoding='utf-8', errors='ignore') as f:
		for line in f:
			m = re.search(r'"\d+"\s+"(.+)"', line)
			if m:
				libs.append(Path(m.group(1)))

	return libs


#Имя игры 

def get_game_name(appid, libraries):
	pattern = re.compile(r'"name"\s+"(.+)"')

	for lib in libraries:
		manifest = lib / "steamapps" / f"appmanifest_{appid}.acf"
		if manifest.exists():
			with open(manifest, 'r', encoding='utf-8', errors='ignore') as f:
				content = f.read()
				m = pattern.search(content)
				if m:
					return m.group(1)
	return f"AppID {appid}"


#Глобальное состояние 

state = {
	"appid": None,
	"speed": "0 Mbps",
	"status": "IDLE"
}

game_cache = {}
last_speed_time = 0
paused = False


#Парсер лога 

def listen_log(log_path):
	global last_speed_time, paused
	speed_re = re.compile(r'Current download rate: ([\d.]+ Mbps)')
	appid_re = re.compile(r'AppID (\d+)')
	paused_re = re.compile(r'Paused')
	with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
		f.seek(0, 2)

		while True:
			line = f.readline()
			if not line:
				time.sleep(1)
				continue
			# Ловим AppID, когда начинается update
			am = appid_re.search(line)
			if am and "update" in line.lower():
				state["appid"] = am.group(1)
			# Ловим паузу
			if paused_re.search(line):
				paused = True
				state["status"] = "PAUSED"
			# Ловим скорость
			sm = speed_re.search(line)
			if sm:
				paused = False
				state["speed"] = sm.group(1)
				last_speed_time = time.time()


#Определение реального статуса 
def compute_status():
	if paused:
		return "PAUSED"
	# если в последние 30 сек была скорость — действительно скачаивает
	if time.time() - last_speed_time < 30:
		return "DOWNLOADING"
	return "IDLE"


#Репорт 

def reporter(libraries):
	for _ in range(1000000):
		time.sleep(1)
		state["status"] = compute_status()
		appid = state["appid"]
		if appid:
			if appid not in game_cache:
				game_cache[appid] = get_game_name(appid, libraries)
			name = game_cache[appid]
		else:
			name = "None"
		print("\n- Steam Download Monitor -")
		print(f"Game:   {name}")
		print(f"AppID:  {appid}")
		print(f"Speed:  {state['speed']}")
		print(f"Status: {state['status']}")
		print("\n")


#main 

def main():
	steam_path = get_steam_path()
	libs = get_libraries(steam_path)
	log_path = steam_path / "logs" / "content_log.txt"
	print("[+] Steam path:", steam_path)
	print("[+] Log file:", log_path)
	t = threading.Thread(target=listen_log, args=(log_path,), daemon=True)
	t.start()
	reporter(libs)


if __name__ == "__main__":
	main()
