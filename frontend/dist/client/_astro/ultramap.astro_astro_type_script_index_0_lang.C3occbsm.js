import{S as U,F as J,P as Y,W as K,k as X,D as Q,l as Z,G as T,m as ee,n as te,i as ne,R as oe,h as w,o as se,M as ae,p as O,q as ie,r as re,s as ce,t as le,u as de}from"./three.module.Dr6T9CDv.js";import{O as pe}from"./OrbitControls.SIkQ7E9P.js";globalThis.process??={};globalThis.process.env??={};const S=[{id:3105,name:"VulnerabilityFixer",x:.5,y:4.4,z:4,target:"CVE-2026-MINIPLASMA",entropy:.85,queue_depth:8.5,error_rate:.02,causal_entropy:.05,cpu_load:.35,role:"Parcheado y asimilación de TVL en Anvil Fuzzer"},{id:3256,name:"AEON_0_DAEMON",x:5.6,y:2.8,z:8.3,target:"JIT_COMPILATION_AST",entropy:.92,queue_depth:12,error_rate:.08,causal_entropy:.12,cpu_load:.72,role:"Compilación JIT y mutagenesis AST en downtime"},{id:6003,name:"SAGE_COUNCIL",x:.3,y:5,z:4.6,target:"TARGET_DARKPOOL_0x1",entropy:.78,queue_depth:4,error_rate:.01,causal_entropy:.22,cpu_load:.15,role:"Deliberación inteligente de targets de red"},{id:3207,name:"OPTIMIZER",x:.7,y:7.5,z:3.5,target:"REFACTOR_LOOP_HEREDADO",entropy:.99,queue_depth:6.5,error_rate:.04,causal_entropy:.08,cpu_load:.95,role:"Refactorización termodinámica de loops heredados"},{id:3045,name:"Jules-Secretario",x:4.5,y:4,z:7.7,target:"GIT_SENTINEL_PR_AUDIT",entropy:.81,queue_depth:15,error_rate:.05,causal_entropy:.02,cpu_load:.45,role:"Orquestación asíncrona de PRs e incidencias Git"},{id:9032,name:"CORTEX-Guard",x:3.2,y:1.4,z:1.3,target:"LEDGER_CHECKPOINT_SIGN",entropy:.95,queue_depth:3,error_rate:.001,causal_entropy:.01,cpu_load:.12,role:"Validación de firmas y checkpoints de ledger"},{id:784,name:"LEA-Ω",x:8.4,y:7.4,z:6,target:"PURGE_PHYSICAL_DISORDER",entropy:.88,queue_depth:9,error_rate:.12,causal_entropy:.15,cpu_load:.65,role:"Loose End Annihilator: purga física de desorden"},{id:8832,name:"Aesthetic-Omega",x:3.2,y:5.2,z:8.4,target:"NOIR_2026_AUDIT_VISUAL",entropy:.97,queue_depth:5,error_rate:.02,causal_entropy:.06,cpu_load:.28,role:"Auditor de componentes y alineación visual Moskv"}],ue="ws://localhost:8081",me=15,ye=window.matchMedia("(prefers-reduced-motion: reduce)").matches,C=document.getElementById("ultramap-canvas-container"),P=document.querySelector(".status-badge"),I=document.getElementById("reality-indicator"),ge=document.getElementById("active-agents-count"),he=document.getElementById("system-exergy-value"),ve=document.getElementById("mean-entropy-value"),B=document.getElementById("bridge-latency"),L=document.getElementById("log-monitor"),xe=document.getElementById("inspect-state"),Ee=document.getElementById("inspector-content"),fe=document.getElementById("exergy-calc"),V=document.getElementById("target-input"),_e=document.getElementById("calc-exergy-btn"),we=document.getElementById("calc-results");let r,c,u,d,l,g,h,_,y=null,G=Date.now(),v=null,p=[...S];const N=new oe,b=new ne;function z(e){if(!e)return{x:0,y:0,z:0};let t=0;for(let n=0;n<e.length;n++)t+=e.charCodeAt(n)*(n+1);const s=t%1e3/100,a=(t>>3)%1e3/100,o=(t>>6)%1e3/100;return{x:s,y:a,z:o}}function R(e,t,s="info"){const a=document.createElement("div");a.className=`log-entry ${s}`;const o=document.createElement("span");for(o.className="log-tag",o.textContent=`[${e}] `,a.append(o,document.createTextNode(t)),L.prepend(a);L.childNodes.length>me;)L.removeChild(L.lastChild)}function A(e,t){P.dataset.mode=e,P.textContent=t}function Ce(e,t){const s=z(t),a=s.x-e.x,o=s.y-e.y,n=s.z-e.z,i=Math.sqrt(a*a+o*o+n*n),m=i*(1/(e.entropy+.001));return{distance:i,target:s,joules:m}}function k(){if(p.length===0)return;ge.textContent=String(p.length);const t=p.reduce((o,n)=>o+n.entropy,0)/p.length;ve.textContent=t.toFixed(3);const a=100-p.reduce((o,n)=>o+(n.error_rate||0),0)/p.length*100;he.textContent=`${Math.max(10,Math.min(100,a)).toFixed(1)}%`}function W(e){v=e,xe.textContent=e.name||`Idx ${e.id}`,fe.classList.remove("hidden");const t=`
				<div class="endocrine-metric">
					<div class="metric-info">
						<span>Dopamine (Queue Depth)</span>
						<strong>${(e.queue_depth||0).toFixed(2)}</strong>
					</div>
					<div class="endocrine-bar"><div class="bar-fill dopamine" style="width: ${Math.min(100,(e.queue_depth||0)*8)}%"></div></div>
				</div>
				<div class="endocrine-metric">
					<div class="metric-info">
						<span>Cortisol (Error Rate)</span>
						<strong class="${(e.error_rate||0)>.05?"warning-text":""}">${((e.error_rate||0)*100).toFixed(1)}%</strong>
					</div>
					<div class="endocrine-bar"><div class="bar-fill cortisol" style="width: ${Math.min(100,(e.error_rate||0)*100)}%"></div></div>
				</div>
				<div class="endocrine-metric">
					<div class="metric-info">
						<span>Serotonin (Causal Entropy)</span>
						<strong>${(e.causal_entropy||0).toFixed(3)}</strong>
					</div>
					<div class="endocrine-bar"><div class="bar-fill serotonin" style="width: ${Math.min(100,(e.causal_entropy||0)*100)}%"></div></div>
				</div>
				<div class="endocrine-metric">
					<div class="metric-info">
						<span>Adrenaline (CPU Load)</span>
						<strong>${((e.cpu_load||0)*100).toFixed(0)}%</strong>
					</div>
					<div class="endocrine-bar"><div class="bar-fill adrenaline" style="width: ${Math.min(100,(e.cpu_load||0)*100)}%"></div></div>
				</div>
			`,s=z(e.target),a=Math.sqrt(Math.pow(s.x-e.x,2)+Math.pow(s.y-e.y,2)+Math.pow(s.z-e.z,2)),o=a*(1/(e.entropy+.001));Ee.innerHTML=`
				<div class="agent-detail-card">
					<div class="detail-row">
						<span class="detail-label">Index</span>
						<strong class="detail-val font-mono">${e.id}</strong>
					</div>
					<div class="detail-row">
						<span class="detail-label">Position</span>
						<strong class="detail-val font-mono">(${e.x.toFixed(2)}, ${e.y.toFixed(2)}, ${e.z.toFixed(2)})</strong>
					</div>
					<div class="detail-row">
						<span class="detail-label">Entropy</span>
						<strong class="detail-val font-mono">${e.entropy.toFixed(3)}</strong>
					</div>
					<div class="detail-row">
						<span class="detail-label">Assigned Target</span>
						<span class="detail-val font-mono target-name" title="${e.target}">${e.target||"None"}</span>
					</div>
					<div class="detail-row">
						<span class="detail-label">Target position</span>
						<strong class="detail-val font-mono">(${s.x.toFixed(2)}, ${s.y.toFixed(2)}, ${s.z.toFixed(2)})</strong>
					</div>
					
					${e.role?`
					<div class="agent-role-block">
						<span class="detail-label">Operative Role</span>
						<p>${e.role}</p>
					</div>`:""}

					<div class="exergy-stats">
						<div class="exergy-stat-mini">
							<span>Topological Distance</span>
							<strong>${a.toFixed(2)} units</strong>
						</div>
						<div class="exergy-stat-mini">
							<span>Active Exergy Cost</span>
							<strong class="highlight-val">${o.toFixed(1)} Joules</strong>
						</div>
					</div>

					<div class="endocrine-matrix-section">
						<span class="surface-label">Endocrinología Volumétrica</span>
						${t}
					</div>
				</div>
			`,$()}function $(){if(!v)return;const e=V.value.trim();if(!e)return;const t=Ce(v,e);we.innerHTML=`
				<div class="calc-results-card">
					<div class="calc-result-row">
						<span>Projected Coordinates:</span>
						<strong class="font-mono">(${t.target.x.toFixed(2)}, ${t.target.y.toFixed(2)}, ${t.target.z.toFixed(2)})</strong>
					</div>
					<div class="calc-result-row">
						<span>Distance to target:</span>
						<strong class="font-mono">${t.distance.toFixed(3)} units</strong>
					</div>
					<div class="calc-result-row">
						<span>Exergy consumption:</span>
						<strong class="highlight-val font-mono">${t.joules.toFixed(2)} Joules</strong>
					</div>
					<div class="calc-formula">
						exergy = distance × (1 / (entropy + 0.001))
					</div>
				</div>
			`}_e.addEventListener("click",$);V.addEventListener("keypress",e=>{e.key==="Enter"&&$()});function Ie(){r=new U,r.fog=new J(657930,.015),c=new Y(60,window.innerWidth/window.innerHeight,.1,1e3),c.position.set(12,12,22),u=new K({antialias:!0,alpha:!0,powerPreference:"high-performance"}),u.setPixelRatio(Math.min(window.devicePixelRatio,2)),u.setSize(C.clientWidth,C.clientHeight),C.appendChild(u.domElement);const e=new X(987694,1.2);r.add(e);const t=new Q(2833381,2.5);t.position.set(10,20,10),r.add(t);const s=new Z(62463,2,50);s.position.set(0,5,0),r.add(s),l=new T,g=new T,h=new T,r.add(l),r.add(g),r.add(h),_=new ee(30,30,2833381,1315866),_.position.y=0,_.material.opacity=.22,_.material.transparent=!0,r.add(_);const a=new te(5);a.position.set(0,.01,0),a.material.opacity=.4,a.material.transparent=!0,r.add(a),d=new pe(c,u.domElement),d.enableDamping=!0,d.dampingFactor=.05,d.rotateSpeed=.6,d.minDistance=5,d.maxDistance=50,window.addEventListener("click",Me),F(),H(),R("SYSTEM","WebGL Engine initialized successfully.")}function F(){for(;l.children.length>0;)l.remove(l.children[0]);for(;g.children.length>0;)g.remove(g.children[0]);for(;h.children.length>0;)h.remove(h.children[0]);const e=new se(.35,16,16);p.forEach(t=>{let s=2833381;t.error_rate>.05?s=15018832:t.queue_depth>10?s=62463:t.entropy>.95&&(s=9317858);const a=new ae({color:s,emissive:s,emissiveIntensity:.25,shininess:30,transparent:!0,opacity:.92}),o=new O(e,a);if(o.position.set(t.x,t.y,t.z),o.userData={agent:t},l.add(o),t.target){const n=z(t.target),i=new ie(.2,.4,4),m=new re({color:58787,wireframe:!0}),f=new O(i,m);f.position.set(n.x,n.y,n.z),f.rotation.x=Math.PI,g.add(f);const x=[];x.push(new w(t.x,t.y,t.z)),x.push(new w(n.x,n.y,n.z));const E=new ce().setFromPoints(x),M=new le({color:2833381,dashSize:.3,gapSize:.15,transparent:!0,opacity:.4}),D=new de(E,M);D.computeLineDistances(),h.add(D)}})}function Me(e){const t=u.domElement.getBoundingClientRect();b.x=(e.clientX-t.left)/t.width*2-1,b.y=-((e.clientY-t.top)/t.height)*2+1,N.setFromCamera(b,c);const s=N.intersectObjects(l.children);if(s.length>0){const a=s[0].object,o=a.userData.agent;l.children.forEach(i=>{i.scale.set(1,1,1),i.material.emissiveIntensity=.25}),a.scale.set(1.4,1.4,1.4),a.material.emissiveIntensity=.8,W(o),R("INSPECT",`Focused on agent: ${o.name||o.id}`);const n=new w(o.x,o.y,o.z);new Promise(i=>{const m=c.position.clone(),f=new w().subVectors(m,n).normalize().multiplyScalar(10),x=new w().addVectors(n,f);let E=0;const M=()=>{E+=.05,E>=1?(c.position.copy(x),d.target.copy(n),i()):(c.position.lerpVectors(m,x,E),d.target.lerpVectors(d.target,n,E),requestAnimationFrame(M))};M()})}}function H(){requestAnimationFrame(H);const e=performance.now()*.001;l.children.forEach((t,s)=>{const a=t.userData.agent,o=1+Math.sin(e*3+s)*.06;v&&v.id===a.id?t.scale.set(1.4*o,1.4*o,1.4*o):t.scale.set(o,o,o)}),g.children.forEach(t=>{t.rotation.y+=.01}),l&&!ye&&(l.rotation.y=Math.sin(e*.05)*.05,g.rotation.y=Math.sin(e*.05)*.05,h.rotation.y=Math.sin(e*.05)*.05),d.update(),u.render(r,c)}function Le(){if(!c||!u)return;const e=C.clientWidth,t=C.clientHeight;c.aspect=e/t,c.updateProjectionMatrix(),u.setSize(e,t)}function j(){A("connecting","CONNECTING"),I.textContent="CONNECTING TO TELEMETRY...",y=new WebSocket(ue),y.onopen=()=>{A("live","C5-REAL"),I.textContent="C5-REAL (LIVE GATEWAY)",I.style.color="var(--success)",R("STREAM","Verifiable lock-free telemetry bridge established.","success")},y.onmessage=e=>{try{const t=JSON.parse(e.data);if(t.type==="FRAME"){const s=t.data,a=Date.now(),o=a-G;if(G=a,B.textContent=`${o}ms`,p=s.map(n=>{const i=S.find(m=>m.id===n.id);return{id:n.id,name:i?i.name:`Agent_${n.id}`,role:i?i.role:"Worker Node",x:n.x,y:n.y,z:n.z,target:n.target,entropy:n.entropy,queue_depth:n.queue_depth,error_rate:n.error_rate,causal_entropy:n.causal_entropy,cpu_load:n.cpu_load}}),F(),k(),v){const n=p.find(i=>i.id===v.id);n&&W(n)}}}catch(t){console.error("Payload error:",t)}},y.onerror=()=>{q()},y.onclose=()=>{q()}}function q(){y&&(y.close(),y=null),A("demo","C4-SIM"),I.textContent="C4-SIM (FALLBACK MODEL)",I.style.color="var(--warning)",B.textContent="0ms",p=[...S],F(),k(),setTimeout(j,5e3)}try{Ie(),j(),window.addEventListener("resize",Le)}catch(e){console.error("Three.js Init failed:",e),A("error","ERROR"),R("ERR","WebGL Engine collapsed.")}
