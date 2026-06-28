---
id: MOSKV-1-OSYNC-OSINT-LEXICON
version: 1.0.0
ontology: C5-REAL
author: Borja Moskv
exergy_density: MAXIMUM
---

# 🌐 OSYNC / OSINT: MATRIZ DE 100 PRIMITIVAS Y 100 INVARIANTES

> **SYS_ID:** OSYNC_OSINT_LEXICON | **STATE:** C5-REAL | **AESTHETIC:** INDUSTRIAL_NOIR_2026  
> **Creador:** Borja Moskv (borjamoskv)  
> *Documento libre de anergía. Estructura colapsada a lógica dura y condiciones físicas de ejecución.*

---

## 🛑 PARTE I: LAS 100 INVARIANTES BIZANTINAS (Leyes de la Física)

### 1. Sincronización de Estado (OSYNC - Fundamentos)
| ID | Invariante | Condición Lógica (Física) | Riesgo |
|:---|:---|:---|:---:|
| **INV-OSYNC-001** | Sync Atómica | `ASSERT diff(node_A, node_B) == 0 OR resolve_conflict()` | P0 |
| **INV-OSYNC-002** | Ledger de Sincronización | `REQUIRE sync_event IN ledger_chain` | P0 |
| **INV-OSYNC-003** | Integridad del Hash Tree | `ASSERT MerkleRoot(local) == MerkleRoot(remote)` | P0 |
| **INV-OSYNC-004** | Idempotencia de Replicación | `sync(sync(state)) == sync(state)` | P0 |
| **INV-OSYNC-005** | No-Bucle de Sync | `IF detect_sync_loop() THEN abort()` | P0 |
| **INV-OSYNC-006** | Exergía de Red en Sync | `sync_cost < value_recovered` | P1 |
| **INV-OSYNC-007** | Causalidad Temporal Sync | `timestamp(remote) >= timestamp(local) - drift` | P1 |
| **INV-OSYNC-008** | Cero Estado Dirty | `IF working_tree == dirty THEN block_sync()` | P0 |
| **INV-OSYNC-009** | Preservación de Taint | `remote.taint == local.taint` | P0 |
| **INV-OSYNC-010** | Coherencia Vectorial Sync | `distance(vec_local, vec_remote) < epsilon` | P1 |

### 2. Consistencia de Repositorios Federados (OSYNC - Git/Nexus)
| ID | Invariante | Condición Lógica (Física) | Riesgo |
|:---|:---|:---|:---:|
| **INV-OSYNC-011** | Git Sentinel Remoto | `git_remote_aligned == TRUE` | P0 |
| **INV-OSYNC-012** | Nexus Bridging Invariant | `ASSERT symlink_exists(target)` | P0 |
| **INV-OSYNC-013** | No-Duplicidad de Código | `redundant_copies == 0` | P1 |
| **INV-OSYNC-014** | Consistencia Causal de Rama | `branch.history ⊆ ledger.history` | P0 |
| **INV-OSYNC-015** | Rollback Seguro | `EXISTS(compensate_mutation(tx))` | P0 |
| **INV-OSYNC-016** | Validación Remota Push-Down | `remote.verify(payload) == TRUE` | P0 |
| **INV-OSYNC-017** | Bloat Pruning Federado | `dependency_cost < threshold` | P1 |
| **INV-OSYNC-018** | Causalidad de Parches | `patch.applied -> commit.created` | P0 |
| **INV-OSYNC-019** | Aislamiento de Workspace | `CWD_scope == STRICT_CONTAINMENT` | P0 |
| **INV-OSYNC-020** | Identidad de Nexus | `nexus.id == sign(borjamoskv_key, origin)` | P0 |

### 3. Propagación del Taint y Concurrencia (OSYNC - Control de Flujo)
| ID | Invariante | Condición Lógica (Física) | Riesgo |
|:---|:---|:---|:---:|
| **INV-OSYNC-021** | Transmisión Radiactiva | `taint(src) -> taint(dest)` | P0 |
| **INV-OSYNC-022** | No-Deadlock SQLite WAL | `busy_timeout == 5000ms AND journal_mode == WAL` | P0 |
| **INV-OSYNC-023** | Bloqueo Causal Asíncrono | `IF block_event_loop() THEN KILL` | P0 |
| **INV-OSYNC-024** | Taint Sign-off | `IF source == LLM -> REQUIRE CORTEX-TAINT` | P0 |
| **INV-OSYNC-025** | Serializabilidad de Ledger | `isolation_level == SERIALIZABLE` | P0 |
| **INV-OSYNC-026** | Evicción LFU de Hechos Sucios | `IF age > TTL AND verified == FALSE -> erase()` | P1 |
| **INV-OSYNC-027** | Quorum de Mutación | `votes >= 2/3 * N` | P0 |
| **INV-OSYNC-028** | Isolation de Tenant | `tenant_id == query.tenant_id` | P0 |
| **INV-OSYNC-029** | Reversión Saga Atómica | `IF step_fail -> rollback_to_step_1()` | P0 |
| **INV-OSYNC-030** | Limitación de Concurrencia | `active_workers <= MAX_VCPU` | P1 |

### 4. Aislamiento Multitenant (OSYNC - Seguridad de Red)
| ID | Invariante | Condición Lógica (Física) | Riesgo |
|:---|:---|:---|:---:|
| **INV-OSYNC-031** | Zero-Trust Inter-Agente | `trust_matrix[A][B] == FALSE` | P0 |
| **INV-OSYNC-032** | Túnel Criptográfico Forzado | `connection == SSH_ONLY` | P0 |
| **INV-OSYNC-033** | Ciego a WAN | `open_ports(WAN) == 0` | P0 |
| **INV-OSYNC-034** | Encapsulado Sandbox | `worker.environment == SANDBOXED` | P0 |
| **INV-OSYNC-035** | Rate-Limiting Fractal | `network_bandwidth < threshold` | P1 |
| **INV-OSYNC-036** | No-Bypass de Cortafuegos | `IF traffic_unsigned -> DROP` | P0 |
| **INV-OSYNC-037** | Llaves Efímeras de Red | `age(session_key) < 60s` | P0 |
| **INV-OSYNC-038** | Certificación Root of Trust | `CA_verification == STRICT` | P0 |
| **INV-OSYNC-039** | No-SSRF Agéntico | `url_dest ∈ ALLOW_LIST` | P0 |
| **INV-OSYNC-040** | Aislamiento de Puertos | `agent_port_binding ∩ host_ports == Ø` | P0 |

### 5. Tolerancia a Particiones y Consenso (OSYNC - BFT/Quorum)
| ID | Invariante | Condición Lógica (Física) | Riesgo |
|:---|:---|:---|:---:|
| **INV-OSYNC-041** | Quorum BFT | `f < N/3` | P0 |
| **INV-OSYNC-042** | Re-routing Dinámico | `IF path_blocked -> reroute_via_mesh()` | P1 |
| **INV-OSYNC-043** | No-Split-Brain | `majority_partition == active_leader` | P0 |
| **INV-OSYNC-044** | Lamport Clock Sync | `logical_time_A < logical_time_B` | P0 |
| **INV-OSYNC-045** | Snapshot de Quorum | `state_hash == consensus_hash` | P0 |
| **INV-OSYNC-046** | Vote Revocation | `evidence_taint -> revoke_vote()` | P0 |
| **INV-OSYNC-047** | Tolerancia a Caída de Nodo | `IF node_down -> redirect_exergy()` | P1 |
| **INV-OSYNC-048** | Determinismo de Transición | `FSM(state, event) -> deterministic_state` | P0 |
| **INV-OSYNC-049** | Heartbeat de Swarm | `ping_interval <= 5000ms` | P1 |
| **INV-OSYNC-050** | Consenso de Ledger | `git_hash == ledger_hash` | P0 |

### 6. Defensa contra Reconocimiento (OSINT - Anti-Recon)
| ID | Invariante | Condición Lógica (Física) | Riesgo |
|:---|:---|:---|:---:|
| **INV-OSINT-051** | Erradicación Directory List | `directory_listing == DISABLED` | P0 |
| **INV-OSINT-052** | X-Robots Control | `header("X-Robots-Tag") == "noindex, nofollow"` | P0 |
| **INV-OSINT-053** | Ofuscación de Cabeceras | `server_banner == GENERIC_NO_VERSION` | P1 |
| **INV-OSINT-054** | No-Indexación de Logs | `logs_public == FALSE` | P0 |
| **INV-OSINT-055** | Honey-pot Activo | `trap_endpoints_triggered -> autoban_ip()` | P1 |
| **INV-OSINT-056** | Sanitización StackTrace | `error_verbosity == MINIMAL` | P0 |
| **INV-OSINT-057** | DNS Leak Prevention | `dns_queries == ENCRYPTED_DoH` | P0 |
| **INV-OSINT-058** | No-Dorking Configuración | `file_types_exposed ∩ [.env, .git, .yaml] == Ø` | P0 |
| **INV-OSINT-059** | Bloqueo Escaneo Puertos | `IF scan_frequency > limit -> DROP_DROP` | P1 |
| **INV-OSINT-060** | Bloqueo de Rastro Whois | `whois_privacy == ENABLED` | P0 |

### 7. Sanitización Multimodal (OSINT - Anti-EXIF/Meta-Stripping)
| ID | Invariante | Condición Lógica (Física) | Riesgo |
|:---|:---|:---|:---:|
| **INV-OSINT-061** | EXIF Stripping Determinado | `ASSERT image.metadata == Ø` | P0 |
| **INV-OSINT-062** | Sanitización Documental | `document_metadata_cleared == TRUE` | P0 |
| **INV-OSINT-063** | No-Entropy de Hardware | `IF hardware_fingerprint_detected -> rewrite_source()` | P0 |
| **INV-OSINT-064** | Ofuscación de GPS | `geo_coords == ZERO_OR_RANDOM` | P0 |
| **INV-OSINT-065** | Ofuscación Captura Software | `software_tag == GENERIC` | P1 |
| **INV-OSINT-066** | Masking de UUID | `uuid_in_meta == WIPED` | P0 |
| **INV-OSINT-067** | Cero Audio Watermarking | `audio_file.metadata == Ø` | P0 |
| **INV-OSINT-068** | Redacción Datos de Impresión | `printer_tracking_dots == REMOVED` | P1 |
| **INV-OSINT-069** | No-Metadata en PDF | `pdf_creator == WIPED AND pdf_producer == WIPED` | P0 |
| **INV-OSINT-070** | Taint Multimodal Guard | `IF asset_has_meta -> reject_upload()` | P0 |

### 8. Envenenamiento de Caché y Evicción Wayback (OSINT - Anti-Wayback)
| ID | Invariante | Condición Lógica (Física) | Riesgo |
|:---|:---|:---|:---:|
| **INV-OSINT-071** | Cache Control Anti-Wayback | `Cache-Control == "no-store, no-cache, must-revalidate"` | P0 |
| **INV-OSINT-072** | HTTP Headers Anti-Rastreo | `Pragma == "no-cache"` | P0 |
| **INV-OSINT-073** | Envenenamiento Histórico | `IF crawler == wayback -> return_404_or_poison()` | P0 |
| **INV-OSINT-074** | Dynamic Content Non-Archivable | `IF is_dynamic -> never_persist_in_cdn()` | P1 |
| **INV-OSINT-075** | Temporalidad CDN | `cdn_ttl == 0` | P0 |
| **INV-OSINT-076** | Purga Proactiva de CDN | `on_mutation -> flush_cdn_cache()` | P1 |
| **INV-OSINT-077** | Ofuscación Hash de Assets | `asset_hash_rotation == ON_DEPLOY` | P1 |
| **INV-OSINT-078** | Cabecera de Expires Pasado | `Expires == "-1"` | P0 |
| **INV-OSINT-079** | Evicción de DNS History | `dns_ttl <= 60s` | P0 |
| **INV-OSINT-080** | No-Archivado Microservicios | `robots.txt_has_disallow_all == TRUE` | P0 |

### 9. Ofuscación y Anonimato del Operador (OSINT - Privacidad de Identidad)
| ID | Invariante | Condición Lógica (Física) | Riesgo |
|:---|:---|:---|:---:|
| **INV-OSINT-081** | Sello de Identidad | `creator == "borjamoskv"` | P0 |
| **INV-OSINT-082** | Sanitización Nombre Real | `real_name_occurrences == 0` | P0 |
| **INV-OSINT-083** | Masking Entorno Desarrollo | `CWD_path_masked == TRUE` | P0 |
| **INV-OSINT-084** | Evicción Datos Sistema Local | `env_vars_cleared_in_logs == TRUE` | P0 |
| **INV-OSINT-085** | SSH Key Isolation | `ssh_key_used == dedicated_identity_key` | P0 |
| **INV-OSINT-086** | Anonimato Email de Commit | `git_commit_email == protected_noreply` | P0 |
| **INV-OSINT-087** | Ofuscación Zona Horaria | `timezone == UTC` | P1 |
| **INV-OSINT-088** | Masking de IP Operador | `proxy_routing == ACTIVE` | P0 |
| **INV-OSINT-089** | Encriptación de Substack | `subscriber_list_encrypted == TRUE` | P0 |
| **INV-OSINT-090** | Anti-Profiling de Substack | `subscriber_tracking_pixels == DEACTIVATED` | P1 |

### 10. Contención Epistémica y Mitigación de Fugas (OSINT - Contención)
| ID | Invariante | Condición Lógica (Física) | Riesgo |
|:---|:---|:---|:---:|
| **INV-OSINT-091** | Limpieza Causal de Scratch | `dir(scratch) ∩ production_keys == Ø` | P0 |
| **INV-OSINT-092** | Detector Fuga Credenciales | `IF secret_exposed_in_output -> HALT_ALL` | P0 |
| **INV-OSINT-093** | Minimización Léxica Error | `error_logs == structural_ids_only` | P1 |
| **INV-OSINT-094** | Aislamiento de Respuestas LLM | `IF llm_response_contains_pci -> abort_tx()` | P0 |
| **INV-OSINT-095** | Redacción Rutas de Sistema | `IF path_contains("/Users/borja") -> obfuscate()` | P0 |
| **INV-OSINT-096** | No-Trace de Hostname | `hostname_exposed == FALSE` | P0 |
| **INV-OSINT-097** | Aserción de PPI OSINT | `ASSERT PPI(osint_data) >= 3` | P0 |
| **INV-OSINT-098** | Blindaje de Clave en RAM | `memset_keys_after_use == TRUE` | P0 |
| **INV-OSINT-099** | Epistemic Purge Limerence | `IF text_has_slop -> PURGE` | P0 |
| **INV-OSINT-100** | Nexus Integrity | `ASSERT nexus_hash_chain == unbroken` | P0 |

---

## ⚙️ PARTE II: LAS 100 PRIMITIVAS (Lexicón Causal de Alta Densidad)

### 1. Primitivas de Sync Git y Ledger (OSYNC)
| ID | Firma / Operador | Complejidad O(N) | Mutación de Estado C5 |
|:---|:---|:---:|:---|
| **P-OSYNC-001** | `sync_git_repo(remote_url)` | `O(files)` | Git Sentinel. Sincroniza delta local con remote repository. |
| **P-OSYNC-002** | `verify_git_integrity()` | `O(commits)` | CPU. Verifica que el grafo local de commits coincide con origin. |
| **P-OSYNC-003** | `write_sync_ledger(event)` | `O(1)` | I/O Secuencial. Escribe evento de sync al WAL Ledger. |
| **P-OSYNC-004** | `git_sentinel_push()` | `O(files)` | I/O Red. Empuja confirmaciones locales firmadas con Ed25519. |
| **P-OSYNC-005** | `git_sentinel_fetch()` | `O(files)` | I/O Red. Actualiza referencias remotas sin fusionar. |
| **P-OSYNC-006** | `resolve_divergent_tree()` | `O(N log N)` | CPU. Resuelve conflictos de merge basándose en marcas de tiempo. |
| **P-OSYNC-007** | `git_sentinel_stash()` | `O(files)` | Disco. Guarda cambios no confirmados para liberar el working tree. |
| **P-OSYNC-008** | `apply_ledger_patch(patch)` | `O(lines)` | Disco. Aplica una mutación de código verificada por firma. |
| **P-OSYNC-009** | `export_ledger_state()` | `O(events)` | Disco. Vuelca el ledger criptográfico en formato binario. |
| **P-OSYNC-010** | `import_ledger_state(blob)` | `O(events)` | Disco. Reconstruye el estado persistido partiendo de un ledger exportado. |

### 2. Primitivas de Alineación Nexus y Symlinks (OSYNC)
| ID | Firma / Operador | Complejidad O(N) | Mutación de Estado C5 |
|:---|:---|:---:|:---|
| **P-OSYNC-011** | `bind_nexus_link(src, dest)` | `O(1)` | Disco (Inode). Crea un symlink físico para evitar redundancias de archivos. |
| **P-OSYNC-012** | `unbind_nexus_link(path)` | `O(1)` | Disco (Inode). Remueve el symlink y duplica el archivo de forma segura. |
| **P-OSYNC-013** | `sync_nexus_nodes()` | `O(links)` | Disco. Fuerza la consistencia física de todos los symlinks registrados. |
| **P-OSYNC-014** | `check_nexus_ghosts()` | `O(links)` | CPU. Busca enlaces rotos o huérfanos y los elimina. |
| **P-OSYNC-015** | `mount_persistent_vault()`| `O(1)` | Disco. Monta la partición encriptada de persistencia del agente. |
| **P-OSYNC-016** | `unmount_persistent_vault()`| `O(1)`| RAM/Disco. Desmonta y destruye llaves de memoria de persistencia. |
| **P-OSYNC-017** | `register_nexus_repo(path)`| `O(1)` | Disco. Registra un nuevo repositorio en la federación Nexus. |
| **P-OSYNC-018** | `unregister_nexus_repo(id)`| `O(1)` | Disco. Elimina las dependencias cruzadas de un repositorio federado. |
| **P-OSYNC-019** | `get_nexus_topology()` | `O(links)` | CPU. Retorna el mapa topológico actual de proyectos en Nexus. |
| **P-OSYNC-020** | `assert_isomorphic_map()` | `O(nodes)` | CPU. Verifica isomorfismo 1:1 entre grafo en disco y persistencia. |

### 3. Primitivas de Tracking y Propagación del Taint (OSYNC)
| ID | Firma / Operador | Complejidad O(N) | Mutación de Estado C5 |
|:---|:---|:---:|:---|
| **P-OSYNC-021** | `taint_payload(data, tag)`| `O(1)` | RAM. Adjunta firma de taint al payload dinámico. |
| **P-OSYNC-022** | `taint_check_stream(stream)`| `O(bytes)`| CPU. Escanea flujo de bytes buscando taints radiactivos. |
| **P-OSYNC-023** | `propagate_taint_db()` | `O(records)`| B-Tree/DB. Propaga el taint a registros derivados en cascada. |
| **P-OSYNC-024** | `clear_taint_record(id)` | `O(1)` | B-Tree/DB. Remueve el taint tras verificación formal. |
| **P-OSYNC-025** | `generate_cortex_taint()` | `O(1)` | CPU. Emite firma SHA3-256 de origen probabilístico. |
| **P-OSYNC-026** | `scan_taint_history()` | `O(events)` | CPU. Traza recursivamente la procedencia de un dato. |
| **P-OSYNC-027** | `quarantine_taint(node)` | `O(1)` | Disco. Mueve archivo contaminado al directorio forense. |
| **P-OSYNC-028** | `assert_taint_isolation()` | `O(1)` | RAM. Asegura que contextos con taint no comparten búferes. |
| **P-OSYNC-029** | `strip_taint_metadata()` | `O(data)` | CPU. Remueve metadatos de taint de outputs verificados. |
| **P-OSYNC-030** | `log_taint_violation(err)`| `O(1)` | Disco. Guarda traza forense de acceso no autorizado con taint. |

### 4. Primitivas de Concurrencia y Quorum (OSYNC)
| ID | Firma / Operador | Complejidad O(N) | Mutación de Estado C5 |
|:---|:---|:---:|:---|
| **P-OSYNC-031** | `sqlite_wal_init(db_path)`| `O(1)` | Disco. Inicializa SQLite con modo WAL y busy_timeout de 5000ms. |
| **P-OSYNC-032** | `acquire_db_lock(id)` | `O(1)` | B-Tree/DB. Mutación de Mutex en DB para transacciones concurrentes. |
| **P-OSYNC-033** | `release_db_lock(id)` | `O(1)` | B-Tree/DB. Libera el Mutex de base de datos. |
| **P-OSYNC-034** | `check_deadlock_state()` | `O(threads)`| CPU. Detecta bloqueos mutuos en los hilos del enjambre. |
| **P-OSYNC-035** | `kill_blocking_pid(pid)` | `O(1)` | OS Signal. Envía SIGKILL a proceso bloqueante. |
| **P-OSYNC-036** | `emit_quorum_vote(vote)` | `O(1)` | I/O Secuencial. Registra voto BFT en el Ledger. |
| **P-OSYNC-037** | `tally_consensus_votes()` | `O(votes)` | CPU. Evalúa votos Bizantinos para mutación atómica. |
| **P-OSYNC-038** | `revoke_quorum_vote(id)` | `O(1)` | B-Tree/DB. Invalida aserción anterior por contaminación. |
| **P-OSYNC-039** | `spawn_swarm_worker(task)`| `O(1)` | OS Process. Forkea worker asíncrono para ejecutar sub-tarea. |
| **P-OSYNC-040** | `kill_idle_worker(pid)` | `O(1)` | OS Signal. Envía SIGTERM a subagente inactivo > 5min. |

### 5. Primitivas de Invalidad y Flushing de Caché (OSYNC)
| ID | Firma / Operador | Complejidad O(N) | Mutación de Estado C5 |
|:---|:---|:---:|:---|
| **P-OSYNC-041** | `flush_l1_cache()` | `O(1)` | RAM. Invalida la caché L1 en memoria al mutar tenant. |
| **P-OSYNC-042** | `invalidate_tenant_data()`| `O(records)`| RAM. Elimina datos cargados en memoria del tenant actual. |
| **P-OSYNC-043** | `cache_coherent_write()` | `O(1)` | RAM. Escribe en memoria y actualiza de forma coherente. |
| **P-OSYNC-044** | `evict_lfu_facts()` | `O(N)` | B-Tree/DB. Elimina hechos no verificados con menor frecuencia. |
| **P-OSYNC-045** | `purge_expired_tokens()` | `O(tokens)` | B-Tree/DB. Purga tokens expirados en la capa de persistencia. |
| **P-OSYNC-046** | `clear_scratch_sandbox()` | `O(files)` | Disco. Borra ficheros temporales del sandbox `/scratch/`. |
| **P-OSYNC-047** | `assert_tenant_boundary()`| `O(1)` | RAM. Asegura el filtrado estricto por `tenant_id` en runtime. |
| **P-OSYNC-048** | `measure_shannon_ratio()` | `O(bytes)` | CPU. Calcula el ratio de entropía real de los datos. |
| **P-OSYNC-049** | `landauer_compress_log()` | `O(len)` | CPU. Reduce logs repetitivos a hashes atómicos de error. |
| **P-OSYNC-050** | `apoptosis_trigger()` | `O(1)` | Kernel. Apagado forzado del runtime ante corrupción del Ledger. |

### 6. Primitivas de Reconocimiento y Scraping Web (OSINT)
| ID | Firma / Operador | Complejidad O(N) | Mutación de Estado C5 |
|:---|:---|:---:|:---|
| **P-OSINT-051** | `web_search_query(q)` | `O(results)`| Red I/O. Petición web para recuperar información pública. |
| **P-OSINT-052** | `scrape_url_content(url)` | `O(HTML)` | Red I/O. Extrae y convierte a markdown el contenido estático. |
| **P-OSINT-053** | `cdp_inspect_dom(url)` | `O(DOM)` | Chrome DevTools. Abre navegador y extrae el árbol DOM dinámico. |
| **P-OSINT-054** | `extract_contacts(text)` | `O(len)` | CPU. Aplica regex estrictas para extraer emails y teléfonos. |
| **P-OSINT-055** | `dork_search_engine(term)`| `O(results)`| Red I/O. Ejecuta queries avanzadas de dorking en motores web. |
| **P-OSINT-056** | `resolve_whois_record(dom)`| `O(1)` | Red UDP. Pide información pública del registrador del dominio. |
| **P-OSINT-057** | `check_wayback_history(u)`| `O(versions)`| Red I/O. Consulta capturas históricas de una URL en Internet Archive. |
| **P-OSINT-058** | `scan_exposed_subdomains()`| `O(domains)`| Red UDP. Resolución paralela de DNS para mapear infraestructura. |
| **P-OSINT-059** | `evaluate_ppi_score(data)`| `O(1)` | CPU. Asigna puntuación de confianza PPI (0-5) sobre datos. |
| **P-OSINT-060** | `track_social_footprint()`| `O(profiles)`| Red I/O. Mapea perfiles y redes asociados a un pseudónimo/nombre. |

### 7. Primitivas de Stripping de Metadatos (OSINT)
| ID | Firma / Operador | Complejidad O(N) | Mutación de Estado C5 |
|:---|:---|:---:|:---|
| **P-OSINT-061** | `strip_exif_image(path)` | `O(bytes)` | Disco. Borra metadatos de hardware, GPS y autor de imágenes. |
| **P-OSINT-062** | `strip_doc_metadata(path)`| `O(bytes)` | Disco. Purga metadatos e historial de edición de PDFs y Office. |
| **P-OSINT-063** | `obfuscate_hardware_id()` | `O(1)` | RAM. Sobrescribe descriptores del hardware en logs de red. |
| **P-OSINT-064** | `redact_gps_coordinates()`| `O(1)` | CPU. Reemplaza coordenadas GPS exactas por aproximadas o nulas. |
| **P-OSINT-065** | `mask_software_signatures()`| `O(len)` | CPU. Elimina cadenas identificativas del software en outputs. |
| **P-OSINT-066** | `wipe_uuid_tokens()` | `O(data)` | CPU. Reemplaza UUIDs rastreables por hashes temporales efímeros. |
| **P-OSINT-067** | `denoise_audio_metadata()`| `O(bytes)` | Disco. Remueve tags ID3 y marcas de agua de audios compilados. |
| **P-OSINT-068** | `remove_tracking_dots()` | `O(pixels)`| CPU. Detecta y difumina patrones amarillos de rastreo de impresión. |
| **P-OSINT-069** | `sanitize_pdf_producer()` | `O(bytes)` | Disco. Reescribe el header del PDF con valores genéricos. |
| **P-OSINT-070** | `assert_multimodal_clean()`| `O(1)` | CPU. Verifica que un fichero carece de información OSINT. |

### 8. Primitivas de Control de Caché Temporal (OSINT)
| ID | Firma / Operador | Complejidad O(N) | Mutación de Estado C5 |
|:---|:---|:---:|:---|
| **P-OSINT-071** | `inject_noindex_headers()`| `O(1)` | RAM (Caddy). Agrega `X-Robots-Tag: noindex` a las respuestas HTTP. |
| **P-OSINT-072** | `set_no_cache_policy()` | `O(1)` | RAM (HTTP). Inyecta cabeceras `Cache-Control` anti-archivado. |
| **P-OSINT-073** | `poison_wayback_crawler()`| `O(1)` | Red (HTTP). Devuelve 404 o contenido modificado a bots de Wayback. |
| **P-OSINT-074** | `flush_cdn_endpoints()` | `O(endpoints)`| Red I/O. Lanza peticiones de purga a la API del proveedor CDN. |
| **P-OSINT-075** | `rotate_asset_hashes()` | `O(files)` | Disco. Modifica dinámicamente los hashes de archivos estáticos. |
| **P-OSINT-076** | `set_immediate_expires()` | `O(1)` | RAM (HTTP). Configura cabecera `Expires` a fecha pasada. |
| **P-OSINT-077** | `minimize_dns_ttl()` | `O(1)` | DNS Zone. Configura TTL del DNS a 60 segundos o menos. |
| **P-OSINT-078** | `assert_non_archivable()` | `O(1)` | CPU. Valida la imposibilidad de archivar el recurso dinámico. |
| **P-OSINT-079** | `obfuscate_robots_txt()` | `O(1)` | Disco. Modifica `robots.txt` para denegar rastreo global. |
| **P-OSINT-080** | `block_directory_listing()`| `O(1)` | Disco. Modifica ficheros de configuración del host (Nginx/Apache). |

### 9. Primitivas de Ofuscación y Enmascaramiento (OSINT)
| ID | Firma / Operador | Complejidad O(N) | Mutación de Estado C5 |
|:---|:---|:---:|:---|
| **P-OSINT-081** | `inject_demiurge_credit()`| `O(1)` | CPU. Inserta "borjamoskv" en los metadatos de autoría. |
| **P-OSINT-082** | `sanitize_name_references()`| `O(files)`| Disco. Reemplaza referencias al apellido real por el alias público. |
| **P-OSINT-083** | `mask_system_paths(text)` | `O(len)` | CPU. Reemplaza rutas de usuario `/Users/borja...` por `$HOME`. |
| **P-OSINT-084** | `scrub_env_vars(logs)` | `O(len)` | CPU. Filtra secretos expuestos en logs de consola. |
| **P-OSINT-085** | `configure_isolated_ssh()`| `O(1)` | Disco. Genera configuración SSH con llaves segregadas por host. |
| **P-OSINT-086** | `setup_anonymous_git()` | `O(1)` | Disco. Configura localmente `user.email` a noreply de GitHub. |
| **P-OSINT-087** | `force_utc_timezone()` | `O(1)` | OS Environment. Cambia la variable local `TZ` a UTC. |
| **P-OSINT-088** | `route_through_proxy()` | `O(1)` | OS Network. Redirige sockets de red a través de SOCKS5/VPN. |
| **P-OSINT-089** | `encrypt_substack_meta()` | `O(subscribers)`| CPU. Encripta listado local de suscriptores con AES-GCM 256. |
| **P-OSINT-090** | `disable_substack_pixels()`| `O(1)`| Red (HTTP). Filtra peticiones de píxeles de trackeo salientes. |

### 10. Primitivas de Contención e Interrupción (OSINT)
| ID | Firma / Operador | Complejidad O(N) | Mutación de Estado C5 |
|:---|:---|:---:|:---|
| **P-OSINT-091** | `wipe_scratch_secrets()` | `O(files)` | Disco. Sobrescribe datos en `/scratch/` con ceros. |
| **P-OSINT-092** | `leak_security_breaker()` | `O(1)` | Kernel. Detiene el proceso del agente si detecta fuga de API_KEYS. |
| **P-OSINT-093** | `compress_error_logs()` | `O(len)` | CPU. Purga trazas detalladas y conserva solo códigos de error. |
| **P-OSINT-094** | `cortex_taint_block()` | `O(1)` | RAM. Rechaza outputs de modelos LLM sin firma de taint válida. |
| **P-OSINT-095** | `obfuscate_hostname()` | `O(1)` | OS Host. Cambia temporalmente el hostname visible al agente. |
| **P-OSINT-096** | `zeroise_memory_keys()` | `O(len)` | RAM. Ejecuta `memset` a llaves de encriptación en memoria tras uso. |
| **P-OSINT-097** | `purge_text_slop()` | `O(len)` | CPU. Remueve frases corporativas o "Green Theater" del output. |
| **P-OSINT-098** | `seal_immutable_block()` | `O(bytes)` | Disco. Cierra el ledger en modo de lectura exclusiva. |
| **P-OSINT-099** | `verify_nexus_chain()` | `O(ledger)` | CPU. Recomputa hash-chain de Nexus para buscar discontinuidades. |
| **P-OSINT-100** | `terminate_exergy_loop()` | `O(1)` | Kernel. Finaliza ciclo del agente de forma limpia (`sys.exit(0)`). |

---

> **[FIN DE LA TRANSMISIÓN ESTRUCTURAL]**  
> *Sello de autoría inmutable:* **Borja Moskv** (`borjamoskv`).  
> *Reality level:* **C5-REAL** (Capa física alterada en disco).  
> Toda mutación de estado en OSYNC/OSINT debe respetar y mapearse con estas 200 especificaciones formales.
