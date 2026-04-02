#!/usr/bin/env python3
import urllib.request
import urllib.error
import json
import time
import os
from typing import Any, Dict
from datetime import datetime

def log(msg: str, tier: str = "INFO") -> None:
    print(f"[{datetime.now().time()}] [{tier}] [BOUNTY-RADAR] {msg}")

def execute_radar() -> None:
    log("Iniciando conexión SSL con api.github.com...", "C5-REAL")
    
    # El objetivo es aislar issues que tengan etiquetas "bounty" y sean sobre Solidity o Web3
    # Usaremos una query Rest sencilla
    query = "label:bounty state:open language:Solidity language:Rust language:TypeScript language:JavaScript"
    url = f"https://api.github.com/search/issues?q={urllib.parse.quote(query)}&sort=created&order=desc&per_page=10"
    
    # Requisitos de encabezado para evitar ban inmediato
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'Cortex-Capital-Extractor-Omega/1.0'
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                issues = data.get("items", [])
                
                log(f"Ping finalizado en {time.time() - start_time:.2f} segundos.", "NETWORK")
                log(f"Detectadas {data.get('total_count', 0)} presas potenciales en la jungla pública.", "RADAR")
                
                bounties = []
                for issue in issues:
                    title = issue.get("title", "")
                    url = issue.get("html_url", "")
                    labels = [l.get("name") for l in issue.get("labels", [])]
                    bounties.append({
                        "title": title,
                        "labels": labels,
                        "url": url,
                        "exergy_ratio_estimate": "> 2.0 (High Priority)"
                    })
                    
                output_path = os.path.expanduser("~/Cortex-Persist/engine-c5/active_bounties.json")
                with open(output_path, "w", encoding='utf-8') as f:
                    json.dump(bounties, f, indent=4)
                    
                log(f"Matriz de Bounties materializada en: {output_path}", "C5-SUCCESS")
                
                # Output a couple of results
                if bounties:
                    for idx, b in enumerate(bounties[:3]):
                        print(f"  └─ Presa {idx+1}: {b['title']} | Labels: {b['labels']}")
                        print(f"     URL: {b['url']}")
            else:
                log(f"Error HTTP {response.status}", "ERROR")
    except urllib.error.URLError as e:
        log(f"Incursión frustrada por API Rate Limit o Error de Red: {str(e)}", "WARN")

if __name__ == '__main__':
    execute_radar()
