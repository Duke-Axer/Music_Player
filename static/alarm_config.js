// static/alarm_config.js

document.addEventListener('DOMContentLoaded', (event) => {
    const alarmForm = document.getElementById('alarmForm');
    
    if (alarmForm) {
        alarmForm.addEventListener('submit', function(event) {
            // Zatrzymaj standardową wysyłkę formularza
            event.preventDefault(); 

            const form = event.target;
            
            // 1. Zbieranie danych
            const name = form.elements.name.value;
            const hour = form.elements.hour.value;
            
            // 2. Zbieranie zaznaczonych dni w postaci listy stringów
            const days = Array.from(form.elements.days)
                              .filter(checkbox => checkbox.checked)
                              .map(checkbox => checkbox.value);

            // 3. Budowanie obiektu JSON
            const dataToSend = {
                name: name,
                hour: hour,
                days: days
            };

            // 4. Wysyłanie żądania POST z poprawnym Content-Type
            fetch('/alarm_add', { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json' 
                },
                body: JSON.stringify(dataToSend)
            })
            .then(response => {
                if (!response.ok) {
                    // Wyrzuć błąd, jeśli status HTTP jest zły (np. 400, 500)
                    return response.json().then(err => { 
                        throw new Error(err.error || `Błąd serwera (Status: ${response.status})`); 
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log('Sukces:', data);
                alert('Alarm zapisany pomyślnie!');
                
                // Przeładowanie strony, aby odświeżyć listę alarmów
                window.location.reload(); 
            })
            .catch((error) => {
                console.error('Błąd Fetch/JSON:', error);
                alert('Wystąpił błąd podczas zapisywania alarmu: ' + error.message);
            });
        });
    }
});