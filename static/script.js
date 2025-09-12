
const API_URL = document.body.dataset.apiUrl;
console.log("🔄 Script loaded");
console.log("📋 API_URL from data attribute:", document.body.dataset.apiUrl);
console.log("📋 Full API URL:", API_URL);

// Pobierz dane z data-atrybutu
const initialState = JSON.parse(document.body.dataset.initialState);
console.log("📦 Dane początkowe:", initialState);


const logEl = document.getElementById("log");
const buttons = document.querySelectorAll("button[data-button]");

const volumeSlider = document.getElementById('volumeSlider');
const volumeValue = document.getElementById('volumeValue');
const rndButton = document.getElementById('rndBtn');
const currentSongEl = document.getElementById("currentSong"); 

let volumeChangeTimeout = null;

// Uaktualnij UI
currentSongEl.textContent = initialState.currentSong || "Brak";
volumeSlider.value = initialState.volume;
volumeValue.textContent = initialState.volume;
updateRandomButton(initialState.isRandom);

// Funkcja do aktualizacji wyglądu przycisku random
function updateRandomButton(isRandom) {
    const rndButton = document.getElementById('rndBtn');
    if (!rndButton) {
        console.error("❌ Przycisk random nie znaleziony!");
        return;
    }
    
    // Aktualizuj wygląd przycisku
    if (isRandom) {
        // Tryb random ON - zielony
        rndButton.textContent = "✅ Random ON";
        rndButton.style.backgroundColor = "green";
        rndButton.style.color = "white";
        rndButton.title = "Tryb random włączony";
    } else {
        // Tryb random OFF - czerwony
        rndButton.textContent = "❌ Random OFF";
        rndButton.style.backgroundColor = "red";
        rndButton.style.color = "white";
        rndButton.title = "Tryb random wyłączony";
    }
    
    // Zapisz stan w data-atrybucie (opcjonalnie)
    rndButton.dataset.randomState = isRandom;
    
    console.log(`🎯 Przycisk random ustawiony na: ${isRandom ? 'ON' : 'OFF'}`);
}


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
      if (rndButton) {
        rndButton.textContent = data.value ? "Random ON" : "Random OFF";
        rndButton.style.backgroundColor = data.value ? "green" : "red";
        log("ustawiono random: " + data.value, "ok");
      }
    }
  if (data.type === "library_update") {
    const songListEl = document.getElementById("songList");
    songListEl.innerHTML = "";

    data.value.forEach((song, index) => {
        const li = document.createElement("li");
        li.textContent = song;
        li.style.cursor = "pointer";

        // klikniecie w piosenkę - wysłanie do serwera
        li.addEventListener("click", () => sendSelectedSong(song, index));

        songListEl.appendChild(li);
    });

    log("Pobrano informacje o albumie", "ok");
}

};

evtSource.onerror = (err) => {
  log("Błąd połączenia z /stream: " + err, "err");
  // Próba ponownego połączenia po 3 sekundach
  setTimeout(() => {
    location.reload();
  }, 3000);
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

// wysyłanie wybranej piosenki
async function sendSelectedSong(song, index) {
    try {
        const res = await fetch("/wybrana-piosenka", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: song, index: index })
        });

        if (!res.ok) {
            console.error("Blad serwera:", res.status);
            return;
        }

        const resp = await res.json();
        console.log("Dostarczono:", resp.status);
    } catch (err) {
        console.error("blad:", err);
    }
}

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
      console.log("Sending data:", { button: buttonId });
	  
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

// Funkcja do pobierania informacji o albumie
async function fetchAlbum() {
    try {
        const res = await fetch("/album", { method: "GET" });
        if (!res.ok) {
            log(`blad pobrania albumu: ${res.status}`, "err");
            return;
        }
        const data = await res.json();  // ["aaa", "bbb", "ccc"]
        console.log("Otrzymano dane albumu:", data);

        // Wy?wietlenie listy piosenek
        const songListEl = document.getElementById("songList");
        songListEl.innerHTML = "";

        data.forEach((song, index) => {
            const li = document.createElement("li");
            li.textContent = song;
            li.style.cursor = "pointer";

            // Obsluga klikniecia w piosenk
            li.addEventListener("click", () => {
                console.log("Wybrano:", song);

                // informacja do serwera o wybranej piosence
                fetch("/wybrana-piosenka", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ title: song, index: index })
                })
                .then(res => res.json())
                .then(resp => console.log("dostarczono", resp.status))
                .catch(err => console.error("blad przy wysylaniu", err));
            });

            songListEl.appendChild(li);
        });

        log("Pobrano informacje o albumie", "ok");
    } catch (e) {
        console.error("Fetch /album error:", e);
        log(`Błąd pobrania albumu: ${e.message}`, "err");
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
// Wywo?ujemy przy starcie
fetchAlbum();
