import json
import subprocess

# CORTEX-PERSIST: Hybrid Router (Strategic Compliance Edition)
from agent_hound_omega import build_mythos_graph
import db
from native_paths import resolve_native_binary
from bounty_guard import BountyGuard
from hitl_handler import HITLHandler

RUST_BIN = resolve_native_binary("cortex-strike", "CORTEX_NATIVE_STRIKE_BIN", "CORTEX_STRIKE_BIN")

def route_target(title, url, exergy):
    print(f"\n[HYBRID] Routing Target: {title} | Sector: {url} | Exergy: {exergy}")

    # Phase 0: Policy Compliance Gate (Mandatory)
    guard = BountyGuard()
    allowed, reason, policy_id = guard.validate_target(url)
    
    if not allowed:
        print(f"[HYBRID-BLOCK] ◈ POLICY VIOLATION: {reason}")
        db.log_intelligence_report("SECURITY", f"Target BLOQUEADO por política: {reason} ({url})", "C5-BLOCKED")
        return

    print(f"[HYBRID-POLICY] ◈ Target Authorized for program: {policy_id}")

    if RUST_BIN is None:
        print(f"[!] Rust native core not found at {RUST_BIN}. Run `cargo build --release` first.")
        return

    # Phase 1: Call Native Rust Strike Engine (VSA Gate)
    res = subprocess.run([str(RUST_BIN), title, url, str(exergy)], capture_output=True, text=True)
    # Output the Rust engine execution log
    for line in res.stdout.split('\n'):
        if not line.startswith("STRIKE_REPORT_JSON:"):
            print(line)

    if res.returncode != 0:
        print(f"[!] Rust core failed: {res.stderr}")
        return

    import re
    # Phase 2: Parse Native Report
    report_json = None
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    for line in res.stdout.split('\n'):
        if "STRIKE_REPORT_JSON:" in line:
            clean_line = ansi_escape.sub('', line)
            raw_json = clean_line.split("STRIKE_REPORT_JSON:")[1].strip()
            
            try:
                report_json = json.loads(raw_json)
            except Exception as e:
                print(f"[!] Decode error: {e}")
            break

    if not report_json:
        print("[!] No structured report returned from Strike Engine.")
        return

    # Phase 3: Cognitive Handoff (If Gate Open)
    if report_json.get("decision") == "HOUND_ACTIVATE":
        vsa_score = report_json.get('vsa_score', 0)
        print(f"\n[HYBRID] ◈ STRIKE GATE IS OPEN (VSA: {vsa_score}%)")
        
        # Phase 1.5: HITL Intercept (Mandatory Human Sign-off)
        print("[HYBRID-HITL] ◈ WAITING FOR HUMAN AUTHORIZATION...")
        hitl = HITLHandler(policy_id)
        auth_msg = f"Authorize Cognitive Handoff for: {title}"
        evidence = f"Native Strike Engine detected high-exergy vulnerability pattern ({vsa_score}% match)."
        
        if not hitl.request_approval(auth_msg, evidence):
            print("[HYBRID-HALT] Human authorization denied. Aborting flow.")
            return

        print(f"\n[HYBRID] ◈ AUTHORIZATION SIGNED ◈ -> Waking CORTEX-HOUND-Omega")
        
        snippet = report_json.get("contract_snippet") 
        if not snippet or snippet == "None":
            snippet = "// Fallback: snippet not provided by native gate."
        
        # Build the LangGraph agent
        engine = build_mythos_graph()
        
        try:
            # Delegate raw intelligence creation to the AI Swarm
            f_state = engine.invoke({  # type: ignore
                "messages": [],
                "bounty_url": url,
                "target_code": snippet,
                "hypotheses": [], "scaffold_commands": [], "proof_of_concept": "",
                "is_verified": False, "iterations": 0
            })

            passed = f_state.get('is_verified', False)
            print(f"\n[HYBRID] ◈ FINAL TRUTH COMPUTED: {'VERIFIED (C5-REAL)' if passed else 'FAILED (C5-PENDING)'}")

            # Seal the Truth in the Sovereign Ledger
            db.store_fact(
                tenant_id="CORTEX-SYSTEM",
                source="HYBRID-ROUTER",
                content=f"Exploit analysis for {url} returned VERIFIED={passed} after HITL-SIGNED cycle.",
                metadata={"subject_key": url, "vsa_score": vsa_score, "is_verified": passed, "hitl": "SIGNED"}
            )
            
            # Post intelligence to the UI Dashboard stream
            status_msg = "VERIFICADO (HITL)" if passed else "BLOQUEADO"
            reality = "C5-REAL" if passed else "C4-FAIL"
            db.log_intelligence_report(
                "SECURITY", 
                f"◈ Native VSA Tensor ({vsa_score}%) → HITL Sign-off → Hound MCTS → Result: {status_msg}", 
                reality
            )
            
            return f_state
            
        except Exception as e:
            print(f"[!] Hound Execution Error: {e}")
            db.log_intelligence_report("SYSTEM", f"Hound execution error: {e}", "C4-FAIL")
            
    else:
        print(f"\n[HYBRID] ◈ STRIKE GATE CLOSED ◈ -> Target Archived.")


if __name__ == "__main__":
    print("∴ CORTEX HYBRID ROUTER (SECURE EDITION) INITIALIZED")
    # Test 1: In-scope (Firedancer)
    t1 = "Firedancer VM exploit prototype"
    u1 = "https://github.com/firedancer-io/firedancer/src/core.c"
    route_target(t1, u1, 9.2)
    
    # Test 2: Out-of-scope
    t2 = "Scraping meta data from API"
    u2 = "https://api.firedancer.io/v1/meta"
    route_target(t2, u2, 4.0)
