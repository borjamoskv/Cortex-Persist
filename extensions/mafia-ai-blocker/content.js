// CORTEX-Persist: Cognitive Firewall Content Script
// Reality Level: C5-REAL

(function () {
    let bypassActive = false;
    let blacklist = [];

    // Carga inicial de blacklist desde el script blacklist.js cargado en el manifest
    if (typeof MAFIA_AI_BLACKLIST !== 'undefined') {
        blacklist = MAFIA_AI_BLACKLIST;
    } else if (window.MAFIA_AI_BLACKLIST) {
        blacklist = window.MAFIA_AI_BLACKLIST;
    }

    const hostname = window.location.hostname;
    const isTwitter = hostname.includes("twitter.com") || hostname.includes("x.com");
    const isSubstack = hostname.includes("substack.com");
    const isLinkedIn = hostname.includes("linkedin.com");

    // Señales Heurísticas del Ruido Térmico (High Smoke Index)
    const SMOKE_KEYWORDS = [
        "thought leader",
        "growth hack",
        "build in public",
        "solopreneur",
        "personal brand",
        "monetize",
        "newsletter",
        "audience growth",
        "ai wrapper",
        "saas founder",
        "chatgpt prompt",
        "prompt engineering",
        "10x engineer",
        "paradigm shift",
        "synergy",
        "growth engine",
        "marketing strategy",
        "digital agency",
        "make money online"
    ];

    const SMOKE_EMOJIS = ["🧵", "👇", "🚀", "📈", "💡", "💎"];

    /**
     * Incrementa de forma segura el contador de intercepciones
     */
    function incrementObfuscatedCount() {
        chrome.storage.local.get(["obfuscatedCount"], (result) => {
            const count = (result.obfuscatedCount || 0) + 1;
            chrome.storage.local.set({ obfuscatedCount: count });
        });
    }

    /**
     * Obtiene un identificador único para cada publicación para controlar reciclaje en scroll infinito
     */
    function getPostUniqueId(element) {
        if (isTwitter) {
            const statusLink = element.querySelector("a[href*='/status/']");
            if (statusLink) {
                return statusLink.getAttribute("href").split("?")[0];
            }
        } else if (isLinkedIn) {
            const urn = element.getAttribute("data-urn") || element.closest("[data-urn]")?.getAttribute("data-urn");
            if (urn) return urn;
        }
        
        // Fallback: usar una combinación de contenido para generar una clave heurística
        const textElement = isTwitter 
            ? element.querySelector("[data-testid='tweetText']") 
            : element;
        const text = textElement ? textElement.textContent.trim() : "";
        if (text) {
            return `${text.length}_${text.substring(0, 40)}`;
        }
        return null;
    }

    /**
     * Evalúa heurísticas multi-señal en una publicación
     */
    function evaluatePostHeuristics(element) {
        let score = 0;
        const signals = [];
        
        // 1. Detección por Enlaces y Cuentas
        const links = element.querySelectorAll("a[href]");
        links.forEach(link => {
            const href = link.getAttribute("href");
            if (!href) return;
            
            if (isTwitter) {
                try {
                    let path = href;
                    if (href.startsWith("http")) {
                        const url = new URL(href);
                        path = url.pathname;
                    }
                    const username = path.replace(/^\//, "").split("/")[0].split("?")[0].toLowerCase();
                    
                    const commonPaths = ["home", "explore", "notifications", "messages", "search", "settings", "i", "tos", "privacy", "messages"];
                    if (username && !commonPaths.includes(username)) {
                        if (blacklist.includes(username)) {
                            // ¿Es el autor original?
                            const isAuthor = link.closest("[data-testid='User-Name']") !== null;
                            if (isAuthor) {
                                score += 100; // Bloqueo instantáneo
                                signals.push(`Autor: @${username}`);
                            } else {
                                score += 50; // Mención de cuenta blacklisted
                                signals.push(`Mención: @${username}`);
                            }
                        }
                    }
                } catch (e) {}
            }
            
            if (href.includes(".substack.com")) {
                try {
                    const url = new URL(href);
                    const subdomain = url.hostname.split(".")[0].toLowerCase();
                    if (blacklist.includes(subdomain)) {
                        score += 50;
                        signals.push(`Substack: ${subdomain}`);
                    }
                } catch (e) {}
            }
            
            // Verificación general del blacklist en URLs
            blacklist.forEach(blocked => {
                if (href.toLowerCase().includes(blocked) && !signals.some(s => s.includes(blocked))) {
                    score += 30;
                    signals.push(`Enlace: ${blocked}`);
                }
            });
        });
        
        // 2. Análisis de Texto
        let text = "";
        if (isTwitter) {
            const txtEl = element.querySelector("[data-testid='tweetText']");
            if (txtEl) text = txtEl.textContent;
        } else {
            text = element.textContent;
        }
        
        if (text) {
            const textLower = text.toLowerCase();
            
            // Búsqueda de palabras clave
            SMOKE_KEYWORDS.forEach(kw => {
                if (textLower.includes(kw)) {
                    score += 10;
                    signals.push(`Keyword: "${kw}"`);
                }
            });
            
            // Búsqueda de emojis térmicos
            SMOKE_EMOJIS.forEach(emoji => {
                const count = (text.match(new RegExp(escapeRegExp(emoji), 'g')) || []).length;
                if (count > 0) {
                    score += count * 5;
                    signals.push(`Emoji: ${emoji} (x${count})`);
                }
            });
        }
        
        return {
            shouldCensor: score >= 15,
            score,
            signals
        };
    }

    function escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    /**
     * Censura un nodo aplicando clases CSS y añadiendo overlay XSS-safe
     */
    function censorNode(element, reason) {
        if (element.getAttribute("data-cortex-censored") === "true") return;
        
        element.setAttribute("data-cortex-censored", "true");
        element.classList.add("cortex-censored");
        
        // Ajustar posición para overlay
        const currentPos = window.getComputedStyle(element).position;
        if (currentPos === "static") {
            element.setAttribute("data-cortex-original-position", "static");
            element.style.position = "relative";
        }
        
        // Crear overlay (Robusto frente a XSS usando textContent)
        const overlay = document.createElement("div");
        overlay.className = "cortex-overlay";
        overlay.textContent = `[ BLOQUEO C5-REAL ]\nMotivo: ${reason}\nSmoke Index > 10.0`;
        
        element.appendChild(overlay);
        incrementObfuscatedCount();
    }

    /**
     * Limpia un nodo censurado previamente (para reciclaje de elementos)
     */
    function uncensorNode(element) {
        if (element.getAttribute("data-cortex-censored") === "true") {
            const overlay = element.querySelector(".cortex-overlay");
            if (overlay) {
                overlay.remove();
            }
            element.removeAttribute("data-cortex-censored");
            element.classList.remove("cortex-censored");
            
            // Restaurar posición original si fue modificada
            const origPos = element.getAttribute("data-cortex-original-position");
            if (origPos) {
                element.style.position = origPos;
                element.removeAttribute("data-cortex-original-position");
            }
        }
    }

    /**
     * Escanea el DOM buscando nuevos elementos o elementos reciclados
     */
    function scanDOM() {
        if (bypassActive) return;

        // Selectores optimizados para cada plataforma
        let selectors = "article, .post-preview";
        if (isTwitter) {
            selectors = "article, [data-testid='cellInnerDiv']";
        } else if (isLinkedIn) {
            selectors = ".feed-shared-update-v2, div[data-urn]";
        }

        const targets = document.querySelectorAll(selectors);
        
        targets.forEach(target => {
            // Evitar escanear posts vacíos en Twitter/X que aún no cargan su contenido
            if (isTwitter) {
                const hasText = target.querySelector("[data-testid='tweetText']");
                const hasLinks = target.querySelector("a[href]");
                if (!hasText && !hasLinks) return;
            }

            const postId = getPostUniqueId(target);
            if (!postId) return;

            const lastScannedId = target.getAttribute("data-cortex-post-id");
            
            // Si el post ha cambiado (reciclaje de elementos), remover censura previa y reevaluar
            if (lastScannedId && lastScannedId !== postId) {
                uncensorNode(target);
            }
            
            // Si ya fue escaneado para este ID específico, ignorar
            if (lastScannedId === postId) {
                return;
            }

            // Registrar ID escaneado actual
            target.setAttribute("data-cortex-post-id", postId);

            const result = evaluatePostHeuristics(target);
            if (result.shouldCensor) {
                censorNode(target, result.signals.join(" | "));
            }
        });
    }

    // Inicialización del estado del Bypass
    chrome.storage.local.get(["cortex_bypass_active"], (result) => {
        bypassActive = !!result.cortex_bypass_active;
        document.body.classList.toggle("cortex-bypass-active", bypassActive);
        
        // Ejecución inicial si el Firewall está activo
        if (!bypassActive) {
            scanDOM();
        }
    });

    // Escucha cambios de almacenamiento en tiempo real
    chrome.storage.onChanged.addListener((changes, namespace) => {
        if (namespace === "local" && changes.cortex_bypass_active) {
            bypassActive = !!changes.cortex_bypass_active.newValue;
            document.body.classList.toggle("cortex-bypass-active", bypassActive);
            
            if (!bypassActive) {
                // Si se reactiva el Firewall, escanear inmediatamente
                scanDOM();
            }
        }
    });

    // MutationObserver optimizado para scroll infinito con debounce
    let scanTimeout = null;
    const observer = new MutationObserver((mutations) => {
        if (bypassActive) return;
        
        let hasAddedNodes = false;
        for (let i = 0; i < mutations.length; i++) {
            if (mutations[i].addedNodes.length > 0) {
                hasAddedNodes = true;
                break;
            }
        }
        
        if (hasAddedNodes) {
            if (scanTimeout) clearTimeout(scanTimeout);
            scanTimeout = setTimeout(scanDOM, 250);
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });

    // Fallback de escaneo inicial
    setTimeout(scanDOM, 800);
})();
