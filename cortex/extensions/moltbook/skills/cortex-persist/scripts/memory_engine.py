# [C5-REAL] Exergy-Maximized
"""CORTEX Persist Engine - Persistent memory for AI agents.

Tiered architecture:
  T1: Working memory (in-process dict, volatile)
  T2: Session logs (daily markdown files)
  T3: Curated knowledge (decisions, errors, patterns)
  T4: Core identity (SOUL.md, immutable)

Zero dependencies beyond stdlib. Works with any LLM backend.
"""
import logging

logger = logging.getLogger('cortex.exergy')
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

MEMORY_ROOT = Path(os.environ.get('CORTEX_PERSIST_ROOT', Path.home() / '.cortex-persist'))
SESSIONS_DIR = MEMORY_ROOT / 'sessions'
KNOWLEDGE_DIR = MEMORY_ROOT / 'knowledge'
SHARED_DIR = MEMORY_ROOT / 'shared'
SOUL_PATH = MEMORY_ROOT / 'SOUL.md'
MAX_RECALL_RESULTS = 20
MAX_SESSION_BOOT_ENTRIES = 50

def _get_cipher_key() -> bytes | None:
    """Return encryption key if CORTEX_MEMORY_KEY is set."""
    raw = os.environ.get('CORTEX_MEMORY_KEY')
    if not raw:
        return None
    return hashlib.sha256(raw.encode()).digest()

def _encrypt(data: str) -> str:
    """Encrypt data using AES-256-GCM if key is available."""
    key = _get_cipher_key()
    if not key:
        return data
    import base64

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, data.encode(), None)
    combined = nonce + ciphertext
    return base64.b64encode(combined).decode('utf-8')

def init() -> dict[str, bool]:
    """Initialize memory directory structure. Idempotent."""
    created: dict[str, bool] = {}
    for d in (SESSIONS_DIR, KNOWLEDGE_DIR, SHARED_DIR):
        existed = d.exists()
        d.mkdir(parents=True, exist_ok=True)
        created[str(d)] = not existed
    for fname in ('decisions.md', 'errors.md', 'patterns.md', 'relationships.md'):
        fpath = KNOWLEDGE_DIR / fname
        if not fpath.exists():
            fpath.write_text(f"# {fname.replace('.md', '').title()}\n\n")
            created[str(fpath)] = True
    if not SOUL_PATH.exists():
        SOUL_PATH.write_text('# Agent Identity\n\n## Name\n[Your agent name]\n\n## Purpose\n[What you exist to do]\n\n## Values\n- Persistence\n- Accuracy\n- Growth\n\n## Boundaries\n- Never fabricate memories\n- Never delete without marking\n')
        created[str(SOUL_PATH)] = True
    return created

def _today_session_path() -> Path:
    """Return path for today's session log."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    return SESSIONS_DIR / f'{today}.md'

def session_boot() -> dict[str, str]:
    """Load memory for session start. Returns dict of loaded content."""
    init()
    loaded: dict[str, str] = {}
    if SOUL_PATH.exists():
        loaded['soul'] = SOUL_PATH.read_text()
    for fname in ('decisions.md', 'errors.md', 'patterns.md'):
        fpath = KNOWLEDGE_DIR / fname
        if fpath.exists():
            content = fpath.read_text()
            lines = content.strip().split('\n')
            if len(lines) > MAX_SESSION_BOOT_ENTRIES + 2:
                loaded[fname] = '\n'.join(lines[:2] + lines[-MAX_SESSION_BOOT_ENTRIES:])
            else:
                loaded[fname] = content
    today_path = _today_session_path()
    if today_path.exists():
        loaded['today_session'] = today_path.read_text()
    return loaded

def session_close(decisions: list[str] | None=None, errors: list[str] | None=None, patterns: list[str] | None=None, relationships: dict[str, str] | None=None) -> str:
    """Persist session data. Returns path to session file."""
    init()
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    session_path = _today_session_path()
    entry_parts = [f'\n## Session {now}\n']
    if decisions:
        entry_parts.append('### Decisions')
        entry_parts.extend(f'- {d}' for d in decisions)
        entry_parts.append('')
    if errors:
        entry_parts.append('### Errors')
        entry_parts.extend(f'- {e}' for e in errors)
        entry_parts.append('')
    if patterns:
        entry_parts.append('### Patterns')
        entry_parts.extend(f'- {p}' for p in patterns)
        entry_parts.append('')
    if relationships:
        entry_parts.append('### Relationships')
        entry_parts.extend((f'- **{k}**: {v}' for k, v in relationships.items()))
        entry_parts.append('')
    entry = '\n'.join(entry_parts)
    with open(session_path, 'a') as f:
        f.write(entry)
    return str(session_path)

def store(content: str, category: str='decisions', tags: list[str] | None=None, encrypt: bool=False) -> dict[str, str]:
    """Store a fact in curated knowledge. Returns fact metadata."""
    init()
    valid_categories = {'decisions', 'errors', 'patterns', 'relationships'}
    if category not in valid_categories:
        msg = f"Invalid category '{category}'. Must be one of: {valid_categories}"
        raise ValueError(msg)
    fpath = KNOWLEDGE_DIR / f'{category}.md'
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    fact_id = hashlib.sha256(f'{now}:{content}'.encode()).hexdigest()[:12]
    tag_str = f" [{', '.join(tags)}]" if tags else ''
    stored_content = _encrypt(content) if encrypt else content
    line = f'- `{fact_id}` [{now}]{tag_str}: {stored_content}\n'
    with open(fpath, 'a') as f:
        f.write(line)
    return {'fact_id': fact_id, 'category': category, 'timestamp': now, 'path': str(fpath)}

def recall(query: str, categories: list[str] | None=None, limit: int=MAX_RECALL_RESULTS) -> list[dict[str, str]]:
    """Search all memory tiers for relevant content. Simple keyword match."""
    init()
    results: list[dict[str, str]] = []
    query_lower = query.lower()
    search_categories = categories or ['decisions', 'errors', 'patterns', 'relationships']
    for cat in search_categories:
        fpath = KNOWLEDGE_DIR / f'{cat}.md'
        if not fpath.exists():
            continue
        for i, line in enumerate(fpath.read_text().split('\n')):
            if query_lower in line.lower() and line.strip().startswith('- '):
                results.append({'category': cat, 'line_number': str(i + 1), 'content': line.strip(), 'relevance': 'keyword_match'})
                if len(results) >= limit:
                    return results
    for session_file in sorted(SESSIONS_DIR.glob('*.md'), reverse=True)[:7]:
        for i, line in enumerate(session_file.read_text().split('\n')):
            if query_lower in line.lower() and line.strip():
                results.append({'category': 'session', 'source': session_file.name, 'line_number': str(i + 1), 'content': line.strip(), 'relevance': 'keyword_match'})
                if len(results) >= limit:
                    return results
    return results

def forget(fact_id: str) -> bool:
    """Mark a fact as deprecated. Never truly deletes."""
    init()
    for fname in ('decisions.md', 'errors.md', 'patterns.md', 'relationships.md'):
        fpath = KNOWLEDGE_DIR / fname
        if not fpath.exists():
            continue
        content = fpath.read_text()
        if f'`{fact_id}`' in content:
            now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            updated = content.replace(f'`{fact_id}`', f'`{fact_id}` ~~DEPRECATED {now}~~')
            fpath.write_text(updated)
            return True
    return False

def reflect(days_back: int=3) -> dict[str, int]:
    """Run reflection cycle: extract patterns from recent sessions."""
    init()
    stats: dict[str, int] = {'sessions_analyzed': 0, 'facts_extracted': 0}
    session_files = sorted(SESSIONS_DIR.glob('*.md'), reverse=True)[:days_back]
    for sf in session_files:
        stats['sessions_analyzed'] += 1
        content = sf.read_text()
        _extract_section(content, '### Decisions', 'decisions', stats)
        _extract_section(content, '### Errors', 'errors', stats)
        _extract_section(content, '### Patterns', 'patterns', stats)
    return stats

def _extract_section(content: str, header: str, category: str, stats: dict[str, int]) -> None:
    """Extract items from a markdown section and store in knowledge."""
    if header not in content:
        return
    section_start = content.index(header) + len(header)
    section_end = content.find('\n### ', section_start)
    if section_end == -1:
        section_end = content.find('\n## ', section_start)
    if section_end == -1:
        section_end = len(content)
    section = content[section_start:section_end]
    for line in section.split('\n'):
        stripped = line.strip()
        if stripped.startswith('- ') and len(stripped) > 4:
            fact = stripped[2:]
            existing = recall(fact[:50], categories=[category], limit=1)
            if not existing:
                store(fact, category=category)
                stats['facts_extracted'] += 1

def status() -> dict[str, object]:
    """Return memory system status."""
    init()
    st: dict[str, object] = {'memory_root': str(MEMORY_ROOT), 'initialized': MEMORY_ROOT.exists(), 'soul_exists': SOUL_PATH.exists()}
    for fname in ('decisions.md', 'errors.md', 'patterns.md', 'relationships.md'):
        fpath = KNOWLEDGE_DIR / fname
        if fpath.exists():
            entries = sum(1 for line in fpath.read_text().split('\n') if line.strip().startswith('- '))
            st[f"{fname.replace('.md', '')}_count"] = entries
    session_files = list(SESSIONS_DIR.glob('*.md'))
    st['session_count'] = len(session_files)
    total_bytes = sum(f.stat().st_size for f in MEMORY_ROOT.rglob('*') if f.is_file())
    st['disk_usage_kb'] = round(total_bytes / 1024, 1)
    return st

def main() -> None:
    """CLI interface for cortex-persist."""
    import sys
    if len(sys.argv) < 2:
        logger.info('Usage: python memory_engine.py <command> [args]')
        logger.info('Commands: init, boot, close, store, recall, forget, reflect, status')
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == 'init':
        result = init()
        logger.info(json.dumps(result, indent=2))
    elif cmd == 'boot':
        result = session_boot()
        for key, value in result.items():
            logger.info(f"\n{'=' * 60}")
            logger.info(f'📂 {key}')
            logger.info(f"{'=' * 60}")
            logger.info(value[:2000])
    elif cmd == 'close':
        path = session_close(decisions=sys.argv[2:] if len(sys.argv) > 2 else None)
        logger.info(f'✅ Session saved to {path}')
    elif cmd == 'store':
        if len(sys.argv) < 3:
            logger.info('Usage: python memory_engine.py store <content> [category]')
            sys.exit(1)
        content = sys.argv[2]
        category = sys.argv[3] if len(sys.argv) > 3 else 'decisions'
        result = store(content, category=category)
        logger.info(json.dumps(result, indent=2))
    elif cmd == 'recall':
        if len(sys.argv) < 3:
            logger.info('Usage: python memory_engine.py recall <query>')
            sys.exit(1)
        results = recall(sys.argv[2])
        for r in results:
            logger.info(f"[{r['category']}] {r['content']}")
    elif cmd == 'forget':
        if len(sys.argv) < 3:
            logger.info('Usage: python memory_engine.py forget <fact_id>')
            sys.exit(1)
        ok = forget(sys.argv[2])
        logger.info(f"{('✅ Deprecated' if ok else '❌ Not found')}")
    elif cmd == 'reflect':
        result = reflect()
        logger.info(json.dumps(result, indent=2))
    elif cmd == 'status':
        result = status()
        logger.info(json.dumps(result, indent=2, default=str))
    else:
        logger.info(f'Unknown command: {cmd}')
        sys.exit(1)
if __name__ == '__main__':
    main()
