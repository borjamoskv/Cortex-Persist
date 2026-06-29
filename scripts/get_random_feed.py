# [C5-REAL] Exergy-Maximized
#!/usr/bin/env python3
"""
cat_id: get-random-feed
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""


import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import time

CORTEX_DIR = os.path.expanduser('~/30_CORTEX')
JSON_PATH = os.path.join(CORTEX_DIR, 'public', 'substack_nodes.json')
HISTORY_PATH = os.path.join(CORTEX_DIR, '.cortex_feed_history.json')
TEMP_FEED_PATH = os.path.join(CORTEX_DIR, 'feed.md')
HISTORY_LIMIT = 12
MIN_EXERGY_AVG = 600

HEADERS = [
    "🗜️ Compresión e Invariantes:",
    "⚡ Ensayos y Arquitectura Causal:",
    "🌌 Convergencia y Análisis:",
    "⚙️ Nodos de Tránsito Causal:",
    "🧬 Estructuras de Exergía Completa:",
    "🛡️ Invariantes Estructurales:"
]

CATEGORIES = {
    "TECH": ["ia", "bot", "openai", "embeddings", "antigravity", "xokas", "programadores", "senior", "cortex", "algorithm", "software", "desarrollo"],
    "CRYPTO": ["domains", "ens", "unstoppable", "phishing", "drainer", "eip", "crypto", "blockchain", "tokens"],
    "MUSIC": ["deftones", "nine inch", "manos de topo", "raveros", "rave", "música", "dj", "vj", "auditoría", "kase.o", "camisa", "compuesto", "sonido", "beat"],
    "PHILOSOPHY": ["excepción", "regla", "inmanencia", "singularidad", "epistémica", "matemáticas", "conspiración", "indignación", "wifi", "coherencia", "pensar", "humana"]
}

EMOJI_KEYWORDS = {
    "forense": "🛡️",
    "phishing": "🛡️",
    "drainer": "🛡️",
    "deftones": "🎛️",
    "nine inch": "🎹",
    "manos de topo": "🐭",
    "raveros": "🕺",
    "rave": "🕺",
    "música": "🎧",
    "dj": "🎧",
    "vj": "🎧",
    "auditoría": "🕵️",
    "ia": "🤖",
    "bot": "🤖",
    "openai": "💊",
    "embeddings": "💊",
    "sincronización": "⚙️",
    "economía": "⚙️",
    "excepción": "⚖️",
    "regla": "⚖️",
    "antigravity": "🛹",
    "xokas": "🛹",
    "dominios": "🐐",
    "ens": "🐐",
    "matemáticas": "📐",
    "conspiración": "📐",
    "indignación": "📻",
    "wifi": "📻",
    "coherencia": "🎙️"
}

ACRONYMS = {"IA", "API", "SDK", "OS", "ENS", "EIP", "AST", "RAG", "DNA", "BFT", "CDP", "VSA", "SSE", "UI", "UX", "HTML", "CSS", "JS", "TS", "JSON", "YAML", "SQLite", "SSD", "RAM", "CPU", "GPU", "TPU"}

FALLBACK_EMOJIS = ["🧬", "🔮", "📡", "🛰️", "⛓️", "⚖️", "⚙️", "🔋", "🔑", "🔍"]

def get_emoji_for_title(title: str) -> str:
    title_lower = title.lower()
    for kw, emoji in EMOJI_KEYWORDS.items():
        if kw in title_lower:
            return emoji
    return random.choice(FALLBACK_EMOJIS)

def clean_and_normalize_title(title: str) -> str:
    t = title.strip()
    
    # Purge leading non-alphanumeric characters (like old emojis)
    while t and not t[0].isalnum() and t[0] not in ['"', "'", "“", "”"]:
        t = t[1:].strip()
        
    # Check if title is ALL CAPS (usually disipates aesthetic exergy)
    if t.isupper():
        words = t.split()
        normalized_words = []
        for word in words:
            # Strip punctuation to check for acronyms
            clean_word = "".join(c for c in word if c.isalnum())
            if clean_word in ACRONYMS:
                normalized_words.append(word) # Keep acronym capitalization
            else:
                # Capitalize normal word
                normalized_words.append(word.capitalize())
        t = " ".join(normalized_words)
        
    # Extra formatting for quotes compatibility
    if t.startswith('"') and t.endswith('"') and len(t) > 2:
        t = f"“{t[1:-1]}”"
        
    return t

def get_category(title: str) -> str:
    title_lower = title.lower()
    for cat_name, keywords in CATEGORIES.items():
        if any(kw in title_lower for kw in keywords):
            return cat_name
    return "GENERAL"

def load_history() -> list:
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history: list):
    try:
        with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        sys.stderr.write(f"[C4-SIM] Warning: failed to save history: {e}\n")

def copy_to_clipboard(text: str) -> bool:
    try:
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, text=True)
        process.communicate(input=text)
        return process.returncode == 0
    except Exception:
        return False

def make_ascii_bar(score: int, max_score: int = 1000, width: int = 10) -> str:
    filled_length = int(width * score // max_score)
    bar = "■" * filled_length + "□" * (width - filled_length)
    return f"[{bar}] {score} EX"

def generate_feed(as_json: bool = False):
    if not os.path.exists(JSON_PATH):
        sys.stderr.write(f"Error: {JSON_PATH} not found. Run scripts/export_substack_nodes.py\n")
        sys.exit(1)

    with open(JSON_PATH, encoding='utf-8') as f:
        data = json.load(f)

    valid_posts = [p for p in data if len(p.get('title', '')) > 10 and p.get('exergy_score', 0) >= 500]
    
    if len(valid_posts) < 4:
        sys.stderr.write("Error: Insufficient high-exergy nodes in database.\n")
        sys.exit(1)

    history = load_history()
    filtered_posts = [p for p in valid_posts if p['post_id'] not in history]
    
    if len(filtered_posts) < 8:
        history = history[len(history)//2:]
        filtered_posts = [p for p in valid_posts if p['post_id'] not in history]

    selected_posts = []
    max_attempts = 100
    best_candidate_set = None
    best_candidate_exergy = 0

    for _ in range(max_attempts):
        candidate_set = []
        candidate_cats = set()
        pool_sample = list(filtered_posts)
        random.shuffle(pool_sample)
        
        for post in pool_sample:
            cat = get_category(post['title'])
            if cat not in candidate_cats or len(candidate_cats) >= 4:
                candidate_set.append(post)
                candidate_cats.add(cat)
            if len(candidate_set) == 4:
                break
                
        if len(candidate_set) < 4:
            for post in pool_sample:
                if post not in candidate_set:
                    candidate_set.append(post)
                if len(candidate_set) == 4:
                    break
                    
        avg_exergy = sum(p.get('exergy_score', 0) for p in candidate_set) / 4.0
        if avg_exergy > best_candidate_exergy:
            best_candidate_exergy = avg_exergy
            best_candidate_set = candidate_set
        if avg_exergy >= MIN_EXERGY_AVG:
            break

    selected_posts = best_candidate_set
    avg_exergy = best_candidate_exergy

    header = random.choice(HEADERS)
    feed_items = []
    new_history_entries = []
    
    for post in selected_posts:
        title = clean_and_normalize_title(post['title'])
        emoji = get_emoji_for_title(title)
        url = f"https://borjamoskv.substack.com/p/{post['post_id']}"
        feed_items.append({
            "post_id": post['post_id'],
            "title": title,
            "emoji": emoji,
            "url": url,
            "exergy_score": post.get('exergy_score', 0),
            "category": get_category(post['title'])
        })
        new_history_entries.append(post['post_id'])

    timestamp_nano = time.time_ns()
    payload_to_sign = f"{timestamp_nano}:{json.dumps([p['post_id'] for p in selected_posts])}"
    taint_hash = hashlib.sha3_256(payload_to_sign.encode('utf-8')).hexdigest()[:16]
    taint_sig = f"taint:MOSKV-1:feed:{int(time.time())}:{taint_hash}"

    # Update history
    updated_history = (history + new_history_entries)[-HISTORY_LIMIT:]
    save_history(updated_history)

    if as_json:
        result = {
            "header": header,
            "items": feed_items,
            "exergy_avg": avg_exergy,
            "taint_signature": taint_sig
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # Generate Markdown
    output_lines = [header]
    for item in feed_items:
        output_lines.append(f"• {item['emoji']} [{item['title']}]({item['url']})")
    output_lines.append(f"\n<!-- CORTEX-TAINT: {taint_sig} -->")
    
    final_output = "\n".join(output_lines)
    print(final_output)
    
    # Render detailed telemetry to stderr
    sys.stderr.write("\n" + "="*50 + "\n")
    sys.stderr.write(f"🧠 CORTEX MANIFOLD TELEMETRY | Average Exergy: {avg_exergy:.1f} EX\n")
    sys.stderr.write("="*50 + "\n")
    for item in feed_items:
        bar = make_ascii_bar(item['exergy_score'])
        sys.stderr.write(f"  {item['emoji']} {item['category']:<12} | {bar} | {item['title'][:40]}...\n")
    sys.stderr.write("="*50 + "\n")

    # Clipboard copy with fallback persistence
    if copy_to_clipboard(final_output):
        sys.stderr.write("⚡ [C5-REAL] Copiado al portapapeles de macOS automáticamente.\n")
    else:
        # Fallback to local file persistence
        try:
            with open(TEMP_FEED_PATH, 'w', encoding='utf-8') as f:
                f.write(final_output)
            sys.stderr.write(f"⚠️ [C4-SIM] Portapapeles fallido. Feed persistido en: {TEMP_FEED_PATH}\n")
        except Exception as e:
            sys.stderr.write(f"❌ [C4-SIM] Error guardando archivo temporal: {e}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generator of high exergy Substack Note feeds.")
    parser.add_argument("--json", action="store_true", help="Output feed in structured JSON format.")
    args = parser.parse_args()
    generate_feed(as_json=args.json)
