globalThis.process??={};globalThis.process.env??={};const l="http://127.0.0.1:8000/v0/demo";let c=!1,s=0,o="PASS",d=12,r=0,g=!1;const f=document.getElementById("btn-toggle-mode"),m=document.getElementById("conn-status"),C=document.getElementById("btn-init"),T=document.getElementById("btn-tamper"),w=document.getElementById("btn-audit"),$=document.getElementById("btn-repair"),_=document.getElementById("btn-query-causal"),P=document.getElementById("val-events"),v=document.getElementById("val-integrity"),k=document.getElementById("val-restarts"),R=document.getElementById("val-corruption");document.getElementById("val-root");const i=document.getElementById("integrity-badge"),b=document.getElementById("causal-chain-display"),I=document.getElementById("console-body");function t(e,a,p=!1){const n=document.createElement("div");n.className=`console-row ${p?"error":""}`,n.textContent=`[${e}] ${a}`,I.appendChild(n),I.scrollTop=I.scrollHeight}function u(e,a,p,n){P.textContent=e.toLocaleString(),v.textContent=a,k.textContent=p,R.textContent=n,n>0||a==="compromised"||a==="FAIL"?(v.style.color="var(--danger)",i.textContent="COMPROMISED",i.style.background="rgba(255, 102, 122, 0.14)",i.style.color="#ff9ba8"):e>0?(v.style.color="var(--success)",i.textContent="SECURE",i.style.background="rgba(138, 240, 196, 0.14)",i.style.color="var(--success)"):(v.style.color="var(--text-muted)",i.textContent="WAITING",i.style.background="rgba(255, 255, 255, 0.05)",i.style.color="var(--text-muted)")}async function S(){c=!c,c?(f.textContent="SWITCH TO DEMO",m.textContent="LIVE (PORT 8000)",m.dataset.mode="live",t("SYSTEM","Attaching to local CORTEX FastAPI backend..."),await y()):(f.textContent="SWITCH TO LIVE",m.textContent="STANDBY",m.dataset.mode="standby",t("SYSTEM","Disconnected from backend. Switched to offline demo mode."),u(s,o,d,r))}async function y(){if(c)try{const e=await fetch(`${l}/state`);if(!e.ok)throw new Error("HTTP state fetch failed");const a=await e.json();s=a.events_loaded,d=a.restarts;const n=await(await fetch(`${l}/audit`)).json();r=n.broken_hashes,o=n.integrity==="valid"?"PASS":"FAIL",u(s,o,d,r),t("API",`State synchronized: ${s} events loaded, restarts: ${d}.`)}catch(e){t("API",`Failed to sync backend state: ${e.message}. Reverting to demo mode.`,!0),S()}}async function B(){if(t("LEDGER","Initializing ingestion pipeline of 10,000 events..."),c)try{const a=await(await fetch(`${l}/init`,{method:"POST"})).json();t("API",`Ingestion complete. ${a.events_generated} events registered in SQLite.`),await y()}catch(e){t("API",`Error during ingestion: ${e.message}`,!0)}else s=1e4,o="PASS",r=0,g=!1,u(s,o,d,r),t("SIM","Ingestion simulation complete: 10,000 cryptographic events generated in memory.")}async function L(){if(t("SECURITY","Injecting malicious payload modification into event 9834...",!0),c)try{const a=await(await fetch(`${l}/tamper/9834`,{method:"POST"})).json();t("API","Attack completed: event 9834 payload altered direct-in-DB.",!0),await y()}catch(e){t("API",`Error during tampering: ${e.message}`,!0)}else{if(s<1e4){t("SIM","Cannot tamper event 9834. Ingest events first.",!0);return}g=!0,r=167,o="FAIL",u(s,o,d,r),t("SIM","Malicious modification detected: Event 9834 payload corrupted. All downstream SHA256 hashes invalidated.",!0)}}async function x(){if(t("AUDITOR","Executing cryptographic sequence verification..."),c)try{const a=await(await fetch(`${l}/audit`)).json();t("API",`Audit report: events=${a.events}, integrity=${a.integrity}, broken_hashes=${a.broken_hashes}, tampering=${a.tampering}`),r=a.broken_hashes,o=a.integrity==="valid"?"PASS":"FAIL",u(s,o,d,r)}catch(e){t("API",`Audit request failed: ${e.message}`,!0)}else{if(s===0){t("SIM","Audit failed: ledger is empty.",!0);return}g?t("SIM","AUDIT VERIFICATION FAILED: 167 broken hashes, tampering detected in event 9834.",!0):t("SIM","AUDIT VERIFICATION PASSED: 10,000 blocks correct, zero broken hashes.")}}async function M(){if(t("LEDGER","Recomputating cryptographic hashes to repair chain..."),c)try{const a=await(await fetch(`${l}/repair`,{method:"POST"})).json();t("API",`Repair completed: ${a.message}`),await y()}catch(e){t("API",`Repair request failed: ${e.message}`,!0)}else{if(!g){t("SIM","Ledger is already secure, repair skipped.");return}g=!1,r=0,o="PASS",u(s,o,d,r),t("SIM","Hash chain re-anchored. All 10,000 event blocks are now cryptographically secure.")}}async function q(){if(t("ENGINE","Executing recursive CTE causal query for event 9834..."),c)try{const e=await fetch(`${l}/causal/9834`);if(!e.ok)throw new Error("Causal query failed");const a=await e.json();A(a.event,a.caused_by,a.root_cause,a.causal_path_length,a.hash_chain_verified),t("API",`Causal chain retrieved. Path depth: ${a.causal_path_length} events.`)}catch(e){t("API",`Error fetching causal chain: ${e.message}`,!0)}else{if(s<1e4){t("SIM","Ledger empty. Ingest events first.",!0);return}A(9834,[9833,9788,9701],"user_request_42",184,!g),t("SIM","Recursive trace resolved: 184 causal propagation steps. Verified back to root user request.")}}function A(e,a,p,n,E){b.innerHTML="";const h=document.createElement("div");h.className="causal-box",h.innerHTML=`
				<div class="causal-header">
					<strong>Trace Event #${e}</strong>
					<span class="proof-badge ${E?"valid":"invalid"}">${E?"HASH SECURE":"HASH BREACHED"}</span>
				</div>
				<div class="causal-step current">
					<span class="step-num">9834</span>
					<div class="step-info">
						<strong>Tool Execution</strong>
						<span>payload: {"tool": "web_search", "query": "query_9834"}</span>
					</div>
				</div>
				
				<div class="causal-arrow">▼ caused by</div>

				<div class="causal-step">
					<span class="step-num">9833</span>
					<div class="step-info">
						<strong>Tool Execution</strong>
						<span>payload: {"tool": "web_search", "query": "query_9833"}</span>
					</div>
				</div>

				<div class="causal-arrow">▼ caused by</div>

				<div class="causal-step-skip">... [${n-5} intermediate events omitted] ...</div>

				<div class="causal-arrow">▼ caused by</div>

				<div class="causal-step">
					<span class="step-num">9788</span>
					<div class="step-info">
						<strong>Tool Execution</strong>
						<span>payload: {"tool": "web_search", "query": "query_9788"}</span>
					</div>
				</div>

				<div class="causal-arrow">▼ caused by</div>

				<div class="causal-step">
					<span class="step-num">9701</span>
					<div class="step-info">
						<strong>Tool Execution</strong>
						<span>payload: {"tool": "web_search", "query": "query_9701"}</span>
					</div>
				</div>

				<div class="causal-arrow">▼ caused by</div>

				<div class="causal-step root">
					<span class="step-num">42</span>
					<div class="step-info">
						<strong>Root Cause: user_request</strong>
						<span>payload: {"message": "user_message_001"}</span>
					</div>
				</div>

				<div class="causal-summary">
					<span>Total Causal Depth: <strong>${n} events</strong></span>
					<span>Verifiable Source: <strong>${p}</strong></span>
				</div>
			`,b.appendChild(h)}f.addEventListener("click",S);C.addEventListener("click",B);T.addEventListener("click",L);w.addEventListener("click",x);$.addEventListener("click",M);_.addEventListener("click",q);u(s,o,d,r);
