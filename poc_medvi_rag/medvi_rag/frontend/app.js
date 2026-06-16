document.addEventListener('DOMContentLoaded', () => {
    const executeBtn = document.getElementById('executeBtn');
    const intentInput = document.getElementById('intentInput');
    const jsonOutput = document.getElementById('jsonOutput');
    const loadingIndicator = document.getElementById('loadingIndicator');

    executeBtn.addEventListener('click', async () => {
        const intent = intentInput.value.trim();
        if (!intent) return;

        // UI State: Loading
        executeBtn.disabled = true;
        executeBtn.style.opacity = '0.5';
        loadingIndicator.classList.remove('hidden');
        jsonOutput.textContent = 'Processing RAG vector retrieval & synthesis...';
        jsonOutput.style.color = '#888';

        try {
            const response = await fetch('/api/intent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ intent })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // UI State: Success (Kintsugi/Typing effect mock)
            jsonOutput.style.color = '#00ff00';
            typeWriterEffect(JSON.stringify(data, null, 4));

        } catch (error) {
            jsonOutput.style.color = '#ff3333';
            jsonOutput.textContent = `[SAGA-ABORT] Error: ${error.message}\nMake sure backend is running.`;
        } finally {
            executeBtn.disabled = false;
            executeBtn.style.opacity = '1';
            loadingIndicator.classList.add('hidden');
        }
    });

    function typeWriterEffect(str, outputEl) {
        let i = 0;
        outputEl.textContent = '';
        const interval = setInterval(() => {
            outputEl.textContent += str[i];
            i++;
            if (i >= str.length) clearInterval(interval);
        }, 10);
    }

    // Poll Incubator endpoint
    const incubatorOutputEl = document.getElementById('incubatorOutput');
    async function pollIncubator() {
        try {
            const res = await fetch('/api/incubator');
            const data = await res.json();
            if (data.concepts && data.concepts.length > 0) {
                incubatorOutputEl.textContent = JSON.stringify(data.concepts, null, 2);
            } else {
                incubatorOutputEl.textContent = "// No concepts crystallized yet...";
            }
        } catch (err) {
            console.error("Incubator fetch error:", err);
        }
    }
    setInterval(pollIncubator, 3000);
    pollIncubator();
});
