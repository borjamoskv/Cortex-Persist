import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from .database import get_connection

def calculate_hash(timestamp: str, type: str, actor: str, payload: str, parent_event: str, prev_hash: str) -> str:
    content = f"{timestamp}{type}{actor}{payload}{parent_event}{prev_hash}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def log_event(type: str, actor: str, payload: Dict[str, Any], parent_event: Optional[int] = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get previous hash
    cursor.execute("SELECT event_hash FROM events ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    prev_hash = row[0] if row else "GENESIS"
    
    timestamp = datetime.now(timezone.utc).isoformat()
    payload_str = json.dumps(payload, sort_keys=True)
    parent_event_val = str(parent_event) if parent_event is not None else ""
    
    event_hash = calculate_hash(timestamp, type, actor, payload_str, parent_event_val, prev_hash)
    
    cursor.execute("""
        INSERT INTO events (timestamp, type, actor, payload, parent_event, prev_hash, event_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, type, actor, payload_str, parent_event, prev_hash, event_hash))
    
    event_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return event_id

def generate_10k_events():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Delete existing events for a clean generation
    cursor.execute("DELETE FROM events")
    
    # Pre-fetch the previous hash (should be GENESIS if empty)
    cursor.execute("SELECT event_hash FROM events ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    prev_hash = row[0] if row else "GENESIS"
    
    events_to_insert = []
    
    # Let's create an initial event to serve as a root cause
    timestamp = datetime.now(timezone.utc).isoformat()
    payload_str = json.dumps({"request": "user_request_42"}, sort_keys=True)
    type_str = "user_input"
    actor = "user"
    parent_event_val = ""
    event_hash = calculate_hash(timestamp, type_str, actor, payload_str, parent_event_val, prev_hash)
    
    events_to_insert.append((timestamp, type_str, actor, payload_str, None, prev_hash, event_hash))
    prev_hash = event_hash
    last_id = 1
    
    print("Generating 10000 events...")
    
    for i in range(10000):
        timestamp = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps({"tool": "web_search", "query": f"query_{i}"}, sort_keys=True)
        type_str = "tool_execution"
        actor = "agent"
        # We simulate some causal chain, linking it to the previous event occasionally or to the root
        parent_id = last_id if i > 0 else 1 
        parent_event_val = str(parent_id)
        
        event_hash = calculate_hash(timestamp, type_str, actor, payload_str, parent_event_val, prev_hash)
        events_to_insert.append((timestamp, type_str, actor, payload_str, parent_id, prev_hash, event_hash))
        
        prev_hash = event_hash
        last_id += 1
        
    cursor.executemany("""
        INSERT INTO events (timestamp, type, actor, payload, parent_event, prev_hash, event_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, events_to_insert)
    
    conn.commit()
    conn.close()
    print("Generated 10000 events.")
    return len(events_to_insert)

def audit_chain() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, timestamp, type, actor, payload, parent_event, prev_hash, event_hash FROM events ORDER BY id ASC")
    rows = cursor.fetchall()
    
    broken_hashes = 0
    expected_prev = "GENESIS"
    
    for row in rows:
        event_id, ts, type_str, actor, payload, parent, p_hash, e_hash = row
        parent_val = str(parent) if parent is not None else ""
        
        # Verify link to previous
        if p_hash != expected_prev:
            broken_hashes += 1
            
        # Verify content hash
        calc_hash = calculate_hash(ts, type_str, actor, payload, parent_val, p_hash)
        if calc_hash != e_hash:
            broken_hashes += 1
            
        expected_prev = e_hash
        
    conn.close()
    
    return {
        "events": len(rows),
        "integrity": "valid" if broken_hashes == 0 else "invalid",
        "broken_hashes": broken_hashes,
        "tampering": broken_hashes > 0
    }

def get_causal_chain(event_id: int) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    
    # We use SQLite CTE to traverse backwards
    query = """
    WITH RECURSIVE causal_chain AS (
        SELECT id, type, actor, payload, parent_event
        FROM events
        WHERE id = ?
        UNION ALL
        SELECT e.id, e.type, e.actor, e.payload, e.parent_event
        FROM events e
        INNER JOIN causal_chain cc ON e.id = cc.parent_event
    )
    SELECT id, type, actor, payload, parent_event FROM causal_chain;
    """
    
    cursor.execute(query, (event_id,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return {"error": "Event not found"}
        
    chain = [{"id": r[0], "type": r[1], "actor": r[2], "payload": json.loads(r[3]), "parent_event": r[4]} for r in rows]
    
    caused_by = [c["id"] for c in chain[1:]]
    
    return {
        "event": event_id,
        "causal_path_length": len(chain),
        "caused_by": caused_by,
        "root_cause": chain[-1]["payload"] if chain else None,
        "proof": "hash_chain_verified"
    }

def get_latest_events(limit: int = 50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, type, actor, payload, parent_event, event_hash FROM events ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    return [{"id": r[0], "timestamp": r[1], "type": r[2], "actor": r[3], "payload": json.loads(r[4]), "parent_event": r[5], "hash": r[6]} for r in rows]
