// Sherlock Watson Payload Injector (C5-REAL)
// Ejecuta esto en la consola (F12) de la pestaña de https://audits.sherlock.xyz/watson/CortexPersist

(function injectWatsonPayload() {
    console.log("🚀 [CORTEX] Iniciando inyección de Payload en Sherlock Watson...");

    const payload = {
        title: "VSA mmap File Descriptor Leak leads to Ouroboros Daemon DoS",
        severity: "High", // Suele ser un select o radio button
        details: `The \`persistence.py\` engine in CORTEX utilizes legacy VSA mmap patterns for high-speed silicion-direct access. However, the file descriptors are not deterministically closed during aggressive asynchronous I/O bursts within the Ouroboros Engine, causing the OS to hit \`ulimit -n\` maximums (Resource Exhaustion).

### Impact
Complete Denial of Service (DoS) of the CORTEX persistence architecture. The Daemon crashes and fails to process further ledger transactions, risking state desynchronization.

### Code Snippet
\`\`\`python
# cortex-core/persistence.py
def vsa_mmap_read(self, path):
    f = open(path, "r+b")
    # File descriptor leaks if mmap fails or is un-garbage collected
    return mmap.mmap(f.fileno(), 0)
\`\`\`

### Recommendation
Implement context managers and rigorous \`.close()\` operations bounded by \`try/finally\` blocks, or migrate fully from legacy VSA mmap to deterministic SQLite WAL patterns.`
    };

    // Helper para inyectar texto y disparar eventos de React/Vue
    const setNativeValue = (element, value) => {
        const valueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value")?.set 
                         || Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set;
        if (valueSetter && element) {
            valueSetter.call(element, value);
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
        }
    };

    // 1. Título
    const titleInput = document.querySelector('input[name="title"], input[placeholder*="Title"], input[id*="title"]');
    if (titleInput) {
        setNativeValue(titleInput, payload.title);
        console.log("✅ Título inyectado");
    } else {
        console.warn("⚠️ No se encontró el campo Título.");
    }

    // 2. Vulnerability Details (Markdown)
    const detailsTextarea = document.querySelector('textarea[name="issue"], textarea[name="body"], textarea');
    if (detailsTextarea) {
        setNativeValue(detailsTextarea, payload.details);
        console.log("✅ Detalles inyectados");
    } else {
        console.warn("⚠️ No se encontró el textarea de Detalles.");
    }

    // 3. Severidad (Intenta clickear el botón/radio de 'High')
    const highSeverityBtn = Array.from(document.querySelectorAll('button, label, input')).find(
        el => el.textContent.includes('High') || (el.value && el.value.toLowerCase() === 'high')
    );
    if (highSeverityBtn) {
        highSeverityBtn.click();
        console.log("✅ Severidad High seleccionada");
    } else {
        console.warn("⚠️ No se encontró el selector de severidad High.");
    }

    console.log("✅ [CORTEX] Inyección finalizada. Revisa los datos y pulsa Submit.");
})();
