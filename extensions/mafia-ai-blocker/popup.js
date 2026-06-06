// CORTEX-Persist: Cognitive Firewall Popup Control
// Reality Level: C5-REAL

document.addEventListener('DOMContentLoaded', () => {
    const bypassToggle = document.getElementById('bypassToggle');
    const blockCountEl = document.getElementById('blockCount');
    const statusBanner = document.getElementById('statusBanner');
    const statusDot = document.getElementById('statusDot');
    const statsCard = document.getElementById('statsCard');

    function updateUI(bypassActive) {
        if (bypassActive) {
            statusBanner.textContent = '[ ESTADO: BYPASS ACTIVO ]';
            statusBanner.className = 'status-banner bypass';
            statusDot.className = 'logo-dot bypass';
            statsCard.className = 'card bypass';
        } else {
            statusBanner.textContent = '[ ESTADO: C5-REAL ACTIVO ]';
            statusBanner.className = 'status-banner active';
            statusDot.className = 'logo-dot active';
            statsCard.className = 'card active';
        }
    }

    // Cargar estados iniciales desde chrome.storage
    chrome.storage.local.get(['cortex_bypass_active', 'obfuscatedCount'], (result) => {
        const bypassActive = !!result.cortex_bypass_active;
        bypassToggle.checked = bypassActive;
        updateUI(bypassActive);
        
        if (result.obfuscatedCount !== undefined) {
            blockCountEl.textContent = result.obfuscatedCount;
        }
    });

    // Escuchar el evento de cambio en el interruptor de Bypass
    bypassToggle.addEventListener('change', () => {
        const bypassActive = bypassToggle.checked;
        chrome.storage.local.set({ cortex_bypass_active: bypassActive }, () => {
            updateUI(bypassActive);
        });
    });

    // Escuchar actualizaciones de almacenamiento por si cambian en segundo plano (ej. contador)
    chrome.storage.onChanged.addListener((changes, namespace) => {
        if (namespace === 'local') {
            if (changes.obfuscatedCount) {
                blockCountEl.textContent = changes.obfuscatedCount.newValue;
            }
            if (changes.cortex_bypass_active) {
                const bypassActive = !!changes.cortex_bypass_active.newValue;
                bypassToggle.checked = bypassActive;
                updateUI(bypassActive);
            }
        }
    });
});
