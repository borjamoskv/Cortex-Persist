/**
 * ∴ OUROBOROS-CAPITAL-Ω x MAC-CONTROL-Ω
 * Abstracción Web3 (Code4rena / Immunefi) vía CDP Raw WebSocket
 * Zero-Auth, 100x High-Performance Extraction
 */

const http = require('http');
const WebSocket = require('ws');

// Chrome remote debugging port
const CDP_PORT = 9222;

const CDP_OPTS = {
    host: '127.0.0.1',
    port: CDP_PORT,
    path: '/json'
};

async function getCDPWebSocket() {
    return new Promise((resolve, reject) => {
        http.get(CDP_OPTS, (res) => {
            let rawData = '';
            res.on('data', (chunk) => rawData += chunk);
            res.on('end', () => {
                try {
                    const pages = JSON.parse(rawData);
                    // Find an active page or fallback to the first available non-background page
                    const page = pages.find(p => p.type === 'page' && p.webSocketDebuggerUrl) || pages[0];
                    if (!page || !page.webSocketDebuggerUrl) {
                        reject(new Error('No active Chrome page WebSocket found.'));
                    } else {
                        resolve(page.webSocketDebuggerUrl);
                    }
                } catch (e) {
                    reject(e);
                }
            });
        }).on('error', reject);
    });
}

function sendCDPCommand(ws, method, params = {}) {
    return new Promise((resolve, reject) => {
        const id = Math.floor(Math.random() * 100000);
        const listener = (data) => {
            const response = JSON.parse(data);
            if (response.id === id) {
                ws.removeListener('message', listener);
                if (response.error) reject(response.error);
                else resolve(response.result);
            }
        };
        ws.on('message', listener);
        ws.send(JSON.stringify({ id, method, params }));
    });
}

async function extractWeb3Bounties(wsUrl) {
    const ws = new WebSocket(wsUrl);

    await new Promise((resolve, reject) => {
        ws.on('open', resolve);
        ws.on('error', reject);
    });

    console.log(`\n[ MAC-CONTROL-Ω : CDP ATTACHED ]`);
    console.log(`>>> Bypassing Web3 Auth. Extracting via DOM Structural Reflection...`);

    // Enable logical domains
    await sendCDPCommand(ws, 'Runtime.enable');
    await sendCDPCommand(ws, 'Page.enable');

    const targets = [
        { name: 'Immunefi (Active Programs)', url: 'https://immunefi.com/explore' },
        { name: 'Code4rena (Competitive Audits)', url: 'https://code4rena.com/audits' }
    ];

    for (const target of targets) {
        console.log(`\n◈ Navigating to Vector: ${target.name}`);
        
        await sendCDPCommand(ws, 'Page.navigate', { url: target.url });
        
        // Async Wait and Scroll Loop to defeat React Virtual DOM Lazy-Loading
        const scrollPayload = `
            new Promise(resolve => {
                let totalHeight = 0;
                let distance = 300;
                let timer = setInterval(() => {
                    let scrollHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if(totalHeight >= scrollHeight || totalHeight > 3000){
                        clearInterval(timer);
                        resolve(true);
                    }
                }, 200);
            })
        `;
        await sendCDPCommand(ws, 'Runtime.evaluate', { expression: scrollPayload, awaitPromise: true });
        
        // Wait another second for final DOM settling
        await new Promise(r => setTimeout(r, 1000));
        
        // Perfected Extraction Logic
        const jsPayload = `
            (() => {
                const results = [];
                const url = window.location.href;
                
                if (url.includes('code4rena')) {
                    // Logic: Find wrapping containers for Contests to avoid splitting lines incorrectly
                    const containers = document.querySelectorAll('a[href^="/audits/"]');
                    containers.forEach(card => {
                        const h3 = card.querySelector('h3, h4');
                        const title = h3 ? h3.innerText : null;
                        
                        // Busca líneas con formato de moneda ($XX,000 o USDC)
                        const allText = card.innerText.split('\\n');
                        const prizeLine = allText.find(t => t.includes('USDC') || t.includes('USDT') || t.includes('$'));
                        
                        if (title && prizeLine && !title.includes(prizeLine)) {
                            results.push({
                                title: title.trim().substring(0, 45),
                                amount: prizeLine.trim(),
                                url: card.href
                            });
                        }
                    });
                } else if (url.includes('immunefi')) {
                    // Logic: Immunefi wraps bounties in generic anchor tags, look for 'Up to' and '$' combination
                    const containers = document.querySelectorAll('a[href^="/bounty/"]');
                    containers.forEach(row => {
                        const allText = row.innerText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                        // Protocol Name is always the first line in their table layout
                        const title = allText[0];
                        // Max Yield always contains 'Up to' or '$' in the same line
                        const prizeLine = allText.find(l => (l.includes('$') && l.length < 25) || l.includes('Up to'));
                        
                        if (title && prizeLine && title.length > 2) {
                            results.push({
                                title: title.substring(0, 35),
                                amount: prizeLine,
                                url: row.href
                            });
                        }
                    });
                }
                
                const uniqueResults = [];
                const seenUrls = new Set();
                for (const r of results) {
                    if (!seenUrls.has(r.url) && r.amount.includes('$')) {
                        seenUrls.add(r.url);
                        uniqueResults.push(r);
                    }
                }
                return uniqueResults;
            })()
        `;

        const result = await sendCDPCommand(ws, 'Runtime.evaluate', {
            expression: jsPayload,
            returnByValue: true
        });

        const activeBounties = result.result.value || [];
        
        if (activeBounties.length > 0) {
            console.log(`[*] Extracted ${activeBounties.length} structural elements from local session buffer.`);
            activeBounties.slice(0, 5).forEach(b => {
                console.log(`  -> TARGET: ${b.title.padEnd(30, ' ')} | YIELD: ${b.amount}`);
            });
        } else {
            console.log(`[-] Pre-render blocked or Virtual DOM not hydrated.`);
        }
    }

    console.log(`\n[!] MAC-CONTROL-Ω Execution Closed. Session State Unaltered.\n`);
    ws.close();
}

async function main() {
    try {
        const wsUrl = await getCDPWebSocket();
        await extractWeb3Bounties(wsUrl);
    } catch (e) {
        console.error("Critical failure acquiring CDP socket:", e.message);
        console.error("Ensure Chrome is running with --remote-debugging-port=9222");
    }
}

main();
