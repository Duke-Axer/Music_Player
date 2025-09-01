
const API_URL = "{{ api_url }}";

const logEl = document.getElementById("log");
const buttons = document.querySelectorAll("button[data-button]");

const volumeSlider = document.getElementById('volumeSlider');
const volumeValue = document.getElementById('volumeValue');
const randomSong = document.getElementById('randomSong');
const currentSongEl = document.getElementById("currentSong");

let volumeChangeTimeout = null;

function setBusy(busy) {
  buttons.forEach(b => b.disabled = busy);
}


function log(msg, cls = "") {
  logEl.innerHTML = `<span class="${cls}">${new Date().toLocaleTimeString()} — ${msg}</span>\n` + logEl.innerHTML;
}


const evtSource = new EventSource("/stream");
evtSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Odbiera wiadomosc z serwera

  if (data.type === "song") {
	  currentSongEl.textContent = data.value;
	  log("Odtwarzana piosenka: " + data.value, "ok");
  }

  if (data.type === "volume") {
	  volumeSlider.value = data.value;
	  volumeValue.textContent = data.value;
	  log("Nowa głośność: " + data.value + "%", "ok");
  }
  if (data.type === "random") {
	  randomSong.value = data.value;
	  log("ustawiono: " + data.value, "ok");
  }
};

evtSource.onerror = (err) => {
  log("Błąd połączenia z /stream: " + err, "err");
};

// Obsługa zmiany głośności
volumeSlider.addEventListener('input', (e) => {
	const volume = parseInt(e.target.value);
	volumeValue.textContent = volume;
	
	// Debounce - wysyłaj zmiany dopiero po 300ms od ostatniej zmiany
	clearTimeout(volumeChangeTimeout);
	volumeChangeTimeout = setTimeout(() => {
		changeVolume(volume);
	}, 300);
});

// Funkcja do wysyłania zmiany głośności
async function changeVolume(volume) {
	setBusy(true);
	try {
		const res = await fetch(API_URL, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ button: "volume", volume: volume })
		});

		if (!res.ok) {
			const text = await res.text();
			log(`Błąd zmiany głośności: ${text || res.statusText}`, "err");
		} else {
			log(`Głośność ustawiona na: ${volume}%`, "ok");
		}
	} catch (e) {
		console.error("❌ Volume change error:", e);
		log(`Błąd zmiany głośności: ${e.message}`, "err");
	} finally {
		setBusy(false);
	}
}

async function sendCommand(buttonId) {
  setBusy(true);
  try {
	  console.log("🔄 Sending request to:", API_URL);
	  
	  const res = await fetch(API_URL, {
		  method: "POST",
		  headers: { "Content-Type": "application/json" },
		  body: JSON.stringify({ button: buttonId }),
		  signal: AbortSignal.timeout(5000) // 5 sekund timeout
	  });

	  console.log("✅ Response status:", res.status);
	  const text = await res.text();
	  console.log("📄 Response text:", text);
	  
	  if (!res.ok) {
		  log(`Błąd ${res.status}: ${text || res.statusText}`, "err");
	  } else {
		  try {
			  const json = JSON.parse(text);
			  log(`OK: ${JSON.stringify(json)}`, "ok");
		  } catch {
			  log(`OK: ${text}`, "ok");
		  }
	  }
  } catch (e) {
	  console.error("❌ Fetch error:", e);
	  log(`Błąd połączenia: ${e.message}`, "err");
	  
	  // Dodatkowe informacje diagnostyczne
	  if (e.name === 'TypeError' && e.message.includes('Failed to fetch')) {
		  log('Serwer nie odpowiada. Sprawdź czy Flask jest uruchomiony.', 'err');
	  }
  } finally {
	  setBusy(false);
  }
}

// Obsługa kliknięć
buttons.forEach(btn => {
  btn.addEventListener("click", () => sendCommand(btn.dataset.button));
});

// skróty klawiaturowe: B=before, S=stop, N=next
window.addEventListener("keydown", (e) => {
  if (e.repeat) return;
  const k = e.key.toLowerCase();
  if (k === "b") sendCommand("before");
  if (k === "s") sendCommand("stop");
  if (k === "n") sendCommand("next");
});

// skrót klawiaturowy dla głośności
window.addEventListener('keydown', (e) => {
	if (e.repeat) return;
	const k = e.key.toLowerCase();
	if (k === "arrowup") {
		volumeSlider.value = Math.min(100, parseInt(volumeSlider.value) + 10);
		volumeValue.textContent = volumeSlider.value;
		changeVolume(parseInt(volumeSlider.value));
	}
	if (k === "arrowdown") {
		volumeSlider.value = Math.max(0, parseInt(volumeSlider.value) - 10);
		volumeValue.textContent = volumeSlider.value;
		changeVolume(parseInt(volumeSlider.value));
	}
});
