import sqlite3
import json
import os
import subprocess
import re

# Resolve paths without hardcoding PII
home = os.path.expanduser('~')
cortex_dir = os.path.join(home, '30_CORTEX')
db_path = os.path.join(cortex_dir, 'cortex', 'audit', 'substack_exergy.sqlite')
json_path = os.path.join(cortex_dir, 'scratch', 'substack_posts.json')

# Ensure directory exists
os.makedirs(os.path.dirname(db_path), exist_ok=True)

with open(json_path, 'r') as f:
    posts = json.load(f)

EXERGY_KW = [r'exergía', r'entropía', r'invariante', r'estructural', r'c5-real', r'c4-sim', r'criptográfic', r'ledger', r'soberanía', r'autómata', r'físico', r'matemátic', r'causal', r'bft', r'estado', r'ontología', r'ast', r'sqlite', r'hash', r'colapso', r'isomorfismo', r'determinista', r'termódinámica', r'ouroboros']
ANERGY_KW = [r'espero que', r'lo siento', r'en resumen', r'bienvenidos', r'hola a todos', r'como modelo de lenguaje', r'quizás', r'creo que', r'te presento', r'vamos a ver', r'útil', r'disculpas', r'sin embargo', r'por otro lado', r'obviamente']

conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS substack_nodes (
    post_id INTEGER PRIMARY KEY,
    title TEXT,
    date TEXT,
    wordcount INTEGER,
    exergy_score INTEGER,
    status TEXT
)
''')

c.execute('DELETE FROM substack_nodes')

for p in posts:
    pid = p.get('id', 0)
    title = p.get('title', '') or ''
    desc = p.get('search_engine_description', '') or p.get('subtitle', '') or p.get('description', '') or ''
    body = p.get('truncated_body_text', '') or ''
    content = (title + ' ' + desc + ' ' + body).lower()
    
    score = 500
    ex_hits = sum(len(re.findall(kw, content)) for kw in EXERGY_KW)
    an_hits = sum(len(re.findall(kw, content)) for kw in ANERGY_KW)
    score += (ex_hits * 25) - (an_hits * 50)
    
    wc = p.get('wordcount', 0)
    if wc < 100: score -= 100
    elif 500 <= wc <= 2000: score += 50
    elif wc > 3000: score -= 50
        
    tags = [t.get('name', '').lower() for t in p.get('postTags', [])]
    if any('c5-real' in t or 'exergía' in t or 'sistema' in t for t in tags): score += 100
        
    score = max(1, min(1000, score))
    
    status = 'C5-REAL_RETAIN' if score >= 500 and wc >= 100 else 'APOPTOSIS_PENDING'
    if wc < 50: status = 'TERMINAL_ANERGY'
    
    c.execute('INSERT INTO substack_nodes VALUES (?, ?, ?, ?, ?, ?)', (pid, title, p.get('post_date', ''), wc, score, status))

conn.commit()
conn.close()

# Git Sentinel
subprocess.run(['git', 'add', '-f', db_path, json_path, os.path.join(cortex_dir, 'scratch', 'audit_report.json'), os.path.join(cortex_dir, 'crystallize_audit.py')], cwd=cortex_dir)
subprocess.run(['git', 'commit', '-m', 'feat(entropy): crystallize Substack audit to SQLite matrix and flag nodes for apoptosis'], cwd=cortex_dir)
hash_out = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=cortex_dir, capture_output=True, text=True)
print("LEDGER HASH:", hash_out.stdout.strip())
