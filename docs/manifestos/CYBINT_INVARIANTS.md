<!-- [C5-REAL] Exergy-Maximized -->
# 🕸️ CYBINT: 100 Primitivas, 100 Invariantes & Casos de Uso

> **STATUS:** C5-REAL  
> **DOMAIN:** Cyber Intelligence (CYBINT) / Threat Intelligence  
> **OPERATOR:** borjamoskv

Este documento establece la ontología absoluta de operaciones CYBINT. Cero ruido narrativo. 100 funciones atómicas (Primitivas), 100 leyes inmutables (Invariantes) y 3 topologías de despliegue (Casos de Uso).

---

## 🏗️ PARTE I: 100 PRIMITIVAS CYBINT (Causal Nodes)
*Las Primitivas son verbos. Acciones atómicas y deterministas que colapsan la entropía en inteligencia ejecutable.*

### Dominio 1: Telemetría & Colección (001-010)
- **CYB-P001** | `OP_EXTRACT_ASN`: IPv4/v6 Cruda -> Nodo ASN Determinista.
- **CYB-P002** | `OP_PDNS_RESOLVE`: Dominio Histórico -> Matriz de Resoluciones (Grafo IP).
- **CYB-P003** | `OP_JARM_FINGERPRINT`: TLS Handshake -> Firma Criptográfica del Backend (C2).
- **CYB-P004** | `OP_BANNER_GRAB`: Payload HTTP Response -> Fingerprint de Software Base.
- **CYB-P005** | `OP_WHOIS_HISTORY`: Dominio Temporal -> Registro Inmutable de Identidad (Email/Registrant).
- **CYB-P006** | `OP_EXIF_STRIP`: Artefacto Media -> Metadato de Procedencia Física.
- **CYB-P007** | `OP_UA_PARSE`: Header Estocástico -> Tipología de Actor (OS/Browser).
- **CYB-P008** | `OP_BGP_MAP`: Tabla de Enrutamiento -> Topología Física de Confianza.
- **CYB-P009** | `OP_SSH_HOSTKEY`: Puerto 22 -> Llave Pública Asimétrica de Identidad.
- **CYB-P010** | `OP_DNS_TXT_VERIFY`: Registros MX/SPF/DMARC -> Nivel de Suplantación Tolerado.

### Dominio 2: Análisis de Artefactos / Malware (011-020)
- **CYB-P011** | `OP_HASH_SHA256`: Binario Crudo -> Identificador Criptográfico Único.
- **CYB-P012** | `OP_HASH_SSDEEP`: Payload Múltiple -> Ratio de Similitud Evolutiva (Fuzzy).
- **CYB-P013** | `OP_ASCII_EXTRACT`: Ejecutable Compilado -> Strings Literales (TTPs potenciales).
- **CYB-P014** | `OP_UNPACK_PE`: Binario Ofuscado -> Código Fuente Intermedio (Desempaquetado).
- **CYB-P015** | `OP_SYSCALL_HOOK`: Ejecución en RAM -> Grafo de Llamadas OS Deterministas.
- **CYB-P016** | `OP_MUTEX_SEAL`: Proceso Aislado -> Identificador de Exclusión Mutua (IoC).
- **CYB-P017** | `OP_IAT_PARSE`: Binario PE -> Vector de Intenciones de la API.
- **CYB-P018** | `OP_RICH_HEADER`: Binario Windows -> Telemetría Causal del Compilador.
- **CYB-P019** | `OP_XOR_DECRYPT`: Payload Cifrado -> Carga Útil Ejecutable (Llave estática).
- **CYB-P020** | `OP_ENTROPY_MEASURE`: Sección Binaria -> Ratio de Cifrado/Compresión (0.0-8.0).

### Dominio 3: Caza de Amenazas en Red (021-030)
- **CYB-P021** | `OP_YARA_MATCH`: Flujo PCAP/Disco -> Aserción de Firma de Malware (True/False).
- **CYB-P022** | `OP_JITTER_CALC`: Conexiones TCP Periódicas -> Varianza Temporal (Beaconing).
- **CYB-P023** | `OP_DGA_DETECT`: Dominio DNS -> Probabilidad Algorítmica de Generación.
- **CYB-P024** | `OP_SNI_EXTRACT`: Sesión TLS -> Nombre de Servidor Solicitado (SNI).
- **CYB-P025** | `OP_TUNNEL_ANALYSIS`: Tráfico ICMP/DNS -> Ratio de Carga Útil Anómala.
- **CYB-P026** | `OP_BASE64_DECODE`: Parámetro HTTP Estocástico -> Comando C2 Estructural.
- **CYB-P027** | `OP_FAST_FLUX_MAP`: Dominio DNS -> Matriz Rotativa de Nodos Botnet.
- **CYB-P028** | `OP_ZEEK_PARSE`: Tráfico Raw -> Log Estructurado (conn.log/http.log).
- **CYB-P029** | `OP_NETFLOW_INGEST`: Interfaz Física -> Matriz de Flujos Origen/Destino.
- **CYB-P030** | `OP_ARP_SPOOF_DETECT`: Broadcast L2 -> Invariante de Duplicidad MAC.

### Dominio 4: OSINT / Dark Web (031-040)
- **CYB-P031** | `OP_ONION_SCRAPE`: Nodo Tor -> Volcado Estático de Contenido Ilícito.
- **CYB-P032** | `OP_PGP_EXTRACT`: Perfil Underground -> Clave de Identidad Criptográfica.
- **CYB-P033** | `OP_GITHUB_LEAK`: Repositorio Abierto -> Secretos C5-REAL (Tokens/Keys).
- **CYB-P034** | `OP_PASTEBIN_REGEX`: Dump Raw -> Filtrado de Credenciales o IoCs.
- **CYB-P035** | `OP_ALIAS_CORRELATE`: Handle Estocástico -> Identidad Física Consolidada.
- **CYB-P036** | `OP_RAAS_MONITOR`: Canal Telegram -> Vector de Ataque y Víctimas Confirmadas.
- **CYB-P037** | `OP_DATA_LEAK_PARSE`: Volcado SQL Raw -> PII (Identificadores Personales) Indexados.
- **CYB-P038** | `OP_FOCA_METADATA`: Documento Público -> Red Interna y Software Base.
- **CYB-P039** | `OP_LINKEDIN_GRAPH`: Organización -> Topología Humana de Ataque (Spear Phishing).
- **CYB-P040** | `OP_SHODAN_QUERY`: Dork Específico -> Matriz de Infraestructura Vulnerable Lógica.

### Dominio 5: Modelado de Adversarios (041-050)
- **CYB-P041** | `OP_MITRE_TACTIC`: Intención Cruda -> Nodo Táctico (Ej. T1003).
- **CYB-P042** | `OP_MITRE_TECHNIQUE`: Ejecución Cruda -> Nodo Técnico (Ej. OS Credential Dumping).
- **CYB-P043** | `OP_DIAMOND_ADVERSARY`: Actor Ambiguo -> Entidad Atribucional Determinista.
- **CYB-P044** | `OP_DIAMOND_INFRA`: IP/Dominio Aislado -> Nodo Estructural de Infraestructura (C2).
- **CYB-P045** | `OP_DIAMOND_CAPABILITY`: Artefacto/Malware -> Herramienta Causal Ofensiva.
- **CYB-P046** | `OP_DIAMOND_VICTIM`: Objetivo Aleatorio -> Perfil de Vulnerabilidad Sectorial.
- **CYB-P047** | `OP_TIER_ASSIGN`: Comportamiento -> Rango de Sofisticación Táctica (1-6).
- **CYB-P048** | `OP_MOTIVE_MAP`: Campaña -> Vector de Incentivo (Financiero/Espionaje).
- **CYB-P049** | `OP_CAMPAIGN_GRAPH`: Eventos Discretos -> Árbol de Dependencia Temporal.
- **CYB-P050** | `OP_TTP_DOCUMENT`: Ejecuciones Aleatorias -> Firma de Comportamiento Inmutable (TTP).

### Dominio 6: Enriquecimiento y Correlación (051-060)
- **CYB-P051** | `OP_VT_RELATION`: Hash Aislado -> Grafo de Contacto VT (URLs/Droppers).
- **CYB-P052** | `OP_MISP_INJECT`: IoC Evaluado -> Persistencia en Grafo Compartido (MISP).
- **CYB-P053** | `OP_STIX_NORMALIZE`: Formato Libre -> Objeto JSON STIX Determinista.
- **CYB-P054** | `OP_PIVOT_IP_DOM`: Nodo IP -> Aristas de Nodos Dominio Asociados.
- **CYB-P055** | `OP_PIVOT_DOM_REG`: Nodo Dominio -> Entidad Humana/Organización Registrante.
- **CYB-P056** | `OP_PIVOT_HASH_FAM`: Nodo Hash -> Pertenencia a Grafo de Familia de Malware.
- **CYB-P057** | `OP_LOG_CORRELATE`: Alerta EDR + Flujo FW -> Cadena de Ataque Verificada.
- **CYB-P058** | `OP_PPI_SCORE`: Fuente Cruda -> Índice de Confiabilidad Probabilística (0-5).
- **CYB-P059** | `OP_MALTEGO_GRAPH`: Nodos JSON -> Visualización Topológica de Vértices/Aristas.
- **CYB-P060** | `OP_IOC_DEDUPLICATE`: Base de Datos Ruido -> Set Único de Amenazas Activas.

### Dominio 7: Inteligencia Táctica (061-070)
- **CYB-P061** | `OP_SNORT_RULE`: TTP Causal -> Filtro Estático de Paquetes L3/L4.
- **CYB-P062** | `OP_SIGMA_RULE`: Comportamiento Lógico -> Filtro Agnóstico para SIEM.
- **CYB-P063** | `OP_BLOCKLIST_GEN`: Grafo de Amenaza -> Lista Plana de Denegación (Firewall).
- **CYB-P064** | `OP_FLASH_ALERT`: Inteligencia Crítica -> Emisión Inmediata de Alta Prioridad.
- **CYB-P065** | `OP_REPORT_WRITE`: Datos Caóticos -> Artefacto Analítico Estructurado.
- **CYB-P066** | `OP_SPLUNK_QUERY`: Lógica de Detección -> Búsqueda Transaccional SPL (Search Processing Language).
- **CYB-P067** | `OP_THRESHOLD_DEF`: Frecuencia de Evento -> Límite Termodinámico de Activación de Alerta.
- **CYB-P068** | `OP_PLAYBOOK_DEV`: Táctica Adversaria -> Árbol de Decisión de Respuesta a Incidentes (SOAR).
- **CYB-P069** | `OP_SINKHOLE_DEPLOY`: Dominio C2 Hostil -> Nodo Controlado por Defensor (Blackhole).
- **CYB-P070** | `OP_ENDPOINT_ISOLATE`: Alerta Crítica -> Segmentación Lógica VLAN de Cuarentena.

### Dominio 8: Identidad y Atribución (071-080)
- **CYB-P071** | `OP_TZ_ANALYSIS`: Timestamps Dispersos -> Huso Horario de Operación (Pattern of Life).
- **CYB-P072** | `OP_LINGUISTIC_MAP`: Texto Crudo -> Huella Semántica y Dialectal.
- **CYB-P073** | `OP_POL_CORRELATE`: Logs de Actividad -> Matriz de Horarios de Vida/Trabajo del Atacante.
- **CYB-P074** | `OP_PASS_REUSE`: Dump de Hash -> Vinculación Causal de Cuentas Cruzadas.
- **CYB-P075** | `OP_CHAIN_TRACE`: Dirección Cripto -> Grafo de Flujo Financiero y Cashout.
- **CYB-P076** | `OP_PROXY_MAP`: IP de Salida VPN -> Identificación de Red de Salida Compartida.
- **CYB-P077** | `OP_LETSENCRYPT_META`: Certificado Automático -> Timestamp de Generación (Script Automatizado).
- **CYB-P078** | `OP_DOMAIN_PATTERN`: Nombre DNS -> Algoritmo/Humano de Generación (Naming Convention).
- **CYB-P079** | `OP_SOCIAL_CORRELATE`: Email de Registro -> Conjunto de Perfiles Públicos (OSINT).
- **CYB-P080** | `OP_OS_FINGERPRINT`: TTL y Window Size de TCP -> Tipología Inmutable del Sistema Operativo.

### Dominio 9: Operaciones Adversariales (081-090)
- **CYB-P081** | `OP_HONEYPOT_DEPLOY`: Zona Estática -> Trampa Interactiva Generadora de TTPs.
- **CYB-P082** | `OP_CANARY_INJECT`: Fichero Inactivo -> Beacon Físico de Exfiltración (Alerta Temprana).
- **CYB-P083** | `OP_ADV_SIMULATE`: Firma de Actor (APT) -> Ejecución Empírica Controlada (Red Teaming).
- **CYB-P084** | `OP_DGA_REVENG`: Tráfico DGA Ciego -> Algoritmo Matemático de Predicción.
- **CYB-P085** | `OP_DEOBFUSCATE`: Script Ilegible -> Código Limpio y TTP Evidente.
- **CYB-P086** | `OP_C2_INTERCEPT`: Red Proxy MitM -> Manipulación Activa de Cargas C2.
- **CYB-P087** | `OP_ATTACK_INFRA`: Panel C2 -> Explotación Inversa de la Botnet.
- **CYB-P088** | `OP_BOTNET_INFILTRATE`: Cliente Falso -> Suscripción Pasiva a Comandos C2 (Intel).
- **CYB-P089** | `OP_DECEPTION_OP`: Datos Reales -> Sembrado de Inteligencia Tóxica para Confundir Adversarios.
- **CYB-P090** | `OP_KILLCHAIN_MAP`: Secuencia de Alertas -> Progreso Estructural del Ataque en Fase (1 a 7).

### Dominio 10: Gobernanza de Inteligencia (091-100)
- **CYB-P091** | `OP_CYCLE_AUDIT`: Flujo Desordenado -> Fase Alineada del Ciclo de Inteligencia.
- **CYB-P092** | `OP_PIR_DEFINE`: Amenaza Abstracta -> Requerimiento Prioritario Estricto de Búsqueda.
- **CYB-P093** | `OP_MATURITY_EVAL`: Operaciones Actuales -> Nivel CMMI de Eficiencia en Inteligencia.
- **CYB-P094** | `OP_KPI_ESTABLISH`: Ruido de Alertas -> Métrica de Detección Efectiva (MTTD/MTTR).
- **CYB-P095** | `OP_TLP_ASSIGN`: Reporte -> Etiqueta de Restricción de Diseminación (Red/Amber/Green/Clear).
- **CYB-P096** | `OP_RISK_INTEGRATE`: Inteligencia CYBINT -> Variable de Riesgo Empresarial Cuantificada.
- **CYB-P097** | `OP_COLLECTION_PLAN`: Vacío de Conocimiento -> Vector de Adquisición Planificado.
- **CYB-P098** | `OP_DATA_VALIDATE`: Ingesta Cruda -> Aserción de Integridad y Fidelidad.
- **CYB-P099** | `OP_TRAIN_ANALYST`: Humano Estocástico -> Analista Determinado por Invariantes (CYBINT).
- **CYB-P100** | `OP_AUTOMATE_INTEL`: Tarea Repetitiva -> Pipeline Autopoético de Ingesta (Cero Anergía).

---

## ⚖️ PARTE II: 100 INVARIANTES CYBINT (Leyes Termodinámicas)
*Los Invariantes son verdades inmutables. No cambian con la tecnología; son axiomas del conflicto.*

### Infraestructura y C2 (001-010)
- **CYB-I001** | `INV_INFRA_REUSE`: La infraestructura es costosa; los atacantes siempre la reutilizan.
- **CYB-I002** | `INV_PDNS_IMMUTABILITY`: El pDNS no miente; el historial de resolución sobrevive a la eliminación del registro.
- **CYB-I003** | `INV_JARM_COMPARTMENT`: Los certificados SSL compartimentan el ruido; firmas únicas (JARM) delatan el backend.
- **CYB-I004** | `INV_DGA_ENTROPY`: Los dominios DGA tienen alta entropía pero patrones matemáticos predecibles.
- **CYB-I005** | `INV_OPSEC_DECAY`: Los atacantes siempre cometen errores de configuración (OPSEC fails) al desplegar servidores C2.
- **CYB-I006** | `INV_FASTFLUX_REVEAL`: Fast-Flux oculta la IP, pero expone masivamente la red de bots subyacente.
- **CYB-I007** | `INV_PROXY_CLUSTER`: El uso de proxies comerciales (VPNs/VPS) anonimiza, pero agrupa a atacantes en ASNs de hosting.
- **CYB-I008** | `INV_PORT_SIGNATURE`: Los puertos inusuales (ej. 4444) son firmas inmutables de herramientas por defecto.
- **CYB-I009** | `INV_C2_LIFESPAN`: La vida útil de un dominio C2 es inversamente proporcional a su exposición en feeds.
- **CYB-I010** | `INV_JITTER_ABSENCE`: La ausencia total de jitter en el beaconing delata instantáneamente a un novato o script básico.

### Artefactos y Malware (011-020)
- **CYB-I011** | `INV_HASH_FRAGILITY`: Los hashes (MD5/SHA256) son la métrica más frágil y de menor valor táctico (Pirámide del Dolor).
- **CYB-I012** | `INV_FUZZY_EVOLUTION`: El fuzzy hashing (SSDeep) expone la evolución del código, superando la limitación del hash rígido.
- **CYB-I013** | `INV_STRING_LEAK`: Las cadenas de texto (strings) en binarios a menudo revelan rutas locales y OPSEC fails.
- **CYB-I014** | `INV_PACKER_SIGNATURE`: Los packers ocultan el código, pero el packer mismo se convierte en una firma identificable.
- **CYB-I015** | `INV_TIMESTAMP_FORGERY`: Los timestamps pueden ser falsificados, pero su omisión o patrón los hace rastreables.
- **CYB-I016** | `INV_MUTEX_IOC`: Los Mutex previenen la doble infección, sirviendo involuntariamente como IoCs de alta fidelidad.
- **CYB-I017** | `INV_IAT_INTENT`: Las importaciones de API (IAT) revelan intenciones deterministas del malware antes de ejecutarlo.
- **CYB-I018** | `INV_RICH_HEADER_ID`: El Rich Header identifica de forma única la topología del entorno de compilación de Windows.
- **CYB-I019** | `INV_ENTROPY_INDICATOR`: Alta entropía en una sección de datos asegura matemáticamente la presencia de cifrado o compresión.
- **CYB-I020** | `INV_FILELESS_MEMORY`: El malware Fileless no reside en disco, pero contamina invariablemente la RAM y los volcados.

### Comportamiento del Adversario (021-030)
- **CYB-I021** | `INV_TTP_IMMUTABILITY`: Los TTPs son el indicador más costoso de cambiar para un adversario estructurado.
- **CYB-I022** | `INV_LEAST_EFFORT`: Los atacantes siguen la ley del menor esfuerzo; abusan de herramientas integradas (LotL) siempre.
- **CYB-I023** | `INV_MOTIVE_BIFURCATION`: El espionaje busca persistencia silenciosa; el cibercrimen busca monetización ruidosa.
- **CYB-I024** | `INV_APT_SCHEDULE`: Los grupos APT son burocracias; sus commits operan en husos horarios y días laborables fijos.
- **CYB-I025** | `INV_ATTRIBUTION_PROBABILITY`: La atribución definitiva es un mito; opera sobre Confidence Levels (Probabilidad).
- **CYB-I026** | `INV_FALSE_FLAG`: Las falsas banderas son inyecciones termodinámicas para desviar la atribución a naciones rivales.
- **CYB-I027** | `INV_DIAMOND_MINIMUM`: El Modelo Diamante requiere la validación empírica de al menos dos vértices para ser accionable.
- **CYB-I028** | `INV_TTP_ADAPTATION`: Los atacantes evolucionan sus TTPs como respuesta termodinámica a la publicación de inteligencia.
- **CYB-I029** | `INV_RAAS_DECOUPLING`: El RaaS separa estructuralmente al desarrollador (capability) del afiliado (adversary).
- **CYB-I030** | `INV_ACCESS_COMMODITY`: El acceso inicial (IABs) se mercantiliza, creando cadenas de suministro ofensivas.

### Inteligencia y Datos (031-040)
- **CYB-I031** | `INV_IOC_CONTEXT`: Un IoC sin contexto no es inteligencia, es un bloqueador ciego de firewall.
- **CYB-I032** | `INV_INTEL_DECAY`: La inteligencia perece termodinámicamente; un IoC viejo es un falso positivo garantizado.
- **CYB-I033** | `INV_DATA_ENRICHMENT`: El enriquecimiento de datos reduce axiomáticamente la entropía analítica.
- **CYB-I034** | `INV_EVENT_CORRELATION`: La correlación de eventos aislados colapsa la onda de probabilidad revelando la campaña.
- **CYB-I035** | `INV_DARKWEB_REPUTATION`: Los foros underground son ecosistemas donde la reputación es el único ancla de confianza.
- **CYB-I036** | `INV_LEAK_RETROSPECTIVE`: Una filtración de datos es retrospectiva; la brecha inicial ocurrió meses antes.
- **CYB-I037** | `INV_WHOIS_TRACE`: Las bases históricas Whois son el único registro inmutable de la evolución de una red C2.
- **CYB-I038** | `INV_TLP_HUMAN_TRUST`: TLP es un protocolo social humano, no un mecanismo de segmentación criptográfica.
- **CYB-I039** | `INV_STIX_SYNTAX`: STIX/TAXII aporta orden sintáctico, pero la semántica accionable requiere analistas (o IA).
- **CYB-I040** | `INV_NOISE_OVERLOAD`: Más datos no equivalen a más inteligencia; el volumen sin filtro anula la señal.

### Detección y Respuesta (041-050)
- **CYB-I041** | `INV_IMPERFECT_DETECTION`: La detección 100% es un fallo axiomático; la ciberseguridad debe asumir el compromiso (Assume Breach).
- **CYB-I042** | `INV_SIGMA_OVER_YARA`: YARA busca cadenas estáticas en disco; Sigma detecta comportamientos termodinámicos en logs.
- **CYB-I043** | `INV_HUNTING_ASSUMPTION`: El Threat Hunting asume que todos los controles de barrera (firewalls/AV) ya han fracasado.
- **CYB-I044** | `INV_ALERT_FATIGUE`: Falsos positivos constantes destruyen la exergía cognitiva del analista SOC.
- **CYB-I045** | `INV_MTTD_METRIC`: El MTTD mide la eficiencia del cerebro CYBINT, no la dureza del firewall.
- **CYB-I046** | `INV_ACTIONABLE_ALERT`: Alerta sin contexto accionable debe ser suprimida o es anergía del sistema.
- **CYB-I047** | `INV_HYPOTHESIS_HUNT`: Buscar por hipótesis lógica es termodinámicamente superior a escanear IoCs ciegamente.
- **CYB-I048** | `INV_HONEYPOT_FIDELITY`: Honeypots generan C5-REAL intelligence: cero falsos positivos (todo tráfico allí es ataque).
- **CYB-I049** | `INV_ISOLATION_LIMIT`: El aislamiento de red L2 no erradica el malware; solo frena el movimiento lateral temporalmente.
- **CYB-I050** | `INV_PLAYBOOK_UPDATE`: Playbooks estáticos mueren; deben nutrirse de feeds de inteligencia táctica continua.

### OSINT y Reconocimiento (051-060)
- **CYB-I051** | `INV_INTERNET_MEMORY`: La subida de datos a internet es irreversible (Wayback Machine no olvida).
- **CYB-I052** | `INV_EXIF_BETRAYAL`: Metadatos EXIF son los OPSEC fails más comunes que rompen la barrera físico-cibernética.
- **CYB-I053** | `INV_SOCIAL_ENG_VECTOR`: Redes sociales proporcionan el grafo relacional exacto para ataques Spear Phishing.
- **CYB-I054** | `INV_SHODAN_NEGLIGENCE`: Shodan no es un arma; es un espejo de la entropía y negligencia en configuración.
- **CYB-I055** | `INV_PDNS_GRAPHING`: pDNS reconstruye grafos inmutables de infraestructura adversaria sin tocar sus servidores (OPSEC safe).
- **CYB-I056** | `INV_REPO_LEAK`: Repositorios públicos exponen credenciales C5-REAL a mayor velocidad que el escaneo de puertos.
- **CYB-I057** | `INV_FORUM_DEMAND`: Los foros underground actúan como mercados de futuros predictivos para exploits 0-day.
- **CYB-I058** | `INV_LINKEDIN_HIERARCHY`: LinkedIn expone el organigrama exacto y los privilegios de acceso (Roles) de una víctima.
- **CYB-I059** | `INV_CRYPTO_TRACEABILITY`: La cadena de bloques (Blockchain) es inherentemente anti-OPSEC para flujos de rescate.
- **CYB-I060** | `INV_OSINT_FOUNDATION`: El 80% del perfilado de adversarios se basa axiomáticamente en OSINT antes que en SIGINT/CYBINT cerrado.

### Vulnerabilidades y Exploits (061-070)
- **CYB-I061** | `INV_POC_CRITICALITY`: CVE sin PoC público es entropía latente; CVE con PoC es energía cinética desencadenada.
- **CYB-I062** | `INV_EDGE_EXPLOITATION`: Los atacantes priorizan firewalls y VPNs, el borde de la topología donde no hay EDR.
- **CYB-I063** | `INV_NDAY_PREFERENCE`: Vulnerabilidades N-day no parchadas son estadísticamente preferibles a quemar un 0-day.
- **CYB-I064** | `INV_PATCH_LAG`: El parcheo siempre tiene lag termodinámico respecto al desarrollo de exploits ofensivos.
- **CYB-I065** | `INV_SUPPLY_CHAIN_BLAST`: Comprometer la cadena de suministro amplifica O(N) el radio de explosión del ataque.
- **CYB-I066** | `INV_PATCH_DIFFING`: Diferenciar parches revela axiomáticamente la vulnerabilidad raíz corregida.
- **CYB-I067** | `INV_MEMORY_PRECISION`: ASLR y DEP aumentan la fricción pero no violan las leyes de explotación de memoria.
- **CYB-I068** | `INV_EXPLOIT_COMMODITY`: Exploits funcionales acaban invariablemente en frameworks (Metasploit, Cobalt Strike).
- **CYB-I069** | `INV_DEFAULT_CONFIG_RISK`: Configuración por defecto mata a más servidores que los desbordamientos de búfer complejos.
- **CYB-I070** | `INV_MASS_SCAN_SPEED`: Escaneos masivos de internet comienzan T+15 minutos tras la publicación del PoC.

### Gobernanza y Estrategia (071-080)
- **CYB-I071** | `INV_PIR_NECESSITY`: Inteligencia sin anclaje a Requisitos Prioritarios (PIR) es consumo de anergía.
- **CYB-I072** | `INV_ACTIONABLE_MANDATE`: Reporte sin plan de mitigación accionable no es CYBINT, es periodismo de TI.
- **CYB-I073** | `INV_FEEDBACK_LOOP`: Ausencia de feedback del SOC destruye la calibración analítica de falsos positivos.
- **CYB-I074** | `INV_SHARING_TRUST`: Compartir inteligencia es un dilema del prisionero solucionado mediante trust networks cerradas.
- **CYB-I075** | `INV_AUTOMATION_LIMIT`: Colección automatizada escala a infinito; el análisis causal requiere juicio O(1) in-memory.
- **CYB-I076** | `INV_TACTICAL_VS_STRAT`: Táctica previene el ataque de hoy; Estrategia define el presupuesto del firewall de mañana.
- **CYB-I077** | `INV_CONFIRMATION_BIAS`: Sesgo de confirmación destruye la objetividad topológica del analista.
- **CYB-I078** | `INV_RELIABILITY_SPLIT`: Fiabilidad de fuente y Credibilidad de dato son variables algebraicas separadas.
- **CYB-I079** | `INV_SPEED_OVER_PERFECTION`: Inteligencia CYBINT al 80% hoy previene el ataque; CYBINT al 100% mañana documenta el forense.
- **CYB-I080** | `INV_MATURITY_PRODUCTION`: Nivel máximo de madurez es producir Invariantes empíricas, no consumir feeds externos.

### Criptografía y OPSEC (081-090)
- **CYB-I081** | `INV_CRYPTO_ILLUSION`: Criptografía propia mal implementada aporta entropía negativa comparado con texto plano.
- **CYB-I082** | `INV_RANSOMWARE_ENCRYPTION`: Cifrado asimétrico protege la clave simétrica (velocidad), garantizando la extorsión.
- **CYB-I083** | `INV_TRAFFIC_INFERENCE`: Cifrar el payload no oculta el tamaño, frecuencia, y metadatos del flujo (Traffic Analysis).
- **CYB-I084** | `INV_CODE_REUSE`: Economía criminal fuerza la reutilización de código (Code Reuse) generando firmas estáticas inevitables.
- **CYB-I085** | `INV_OPSEC_FATIGUE`: El OPSEC perfecto requiere energía infinita; el atacante humano se fatiga y falla.
- **CYB-I086** | `INV_VT_BETRAYAL`: Atacantes usan VirusTotal como QA, regalando firmas tempranas a los cazadores YARA.
- **CYB-I087** | `INV_SHARED_INFRA_LINK`: Compartir un email de registro expone el grafo topológico completo de la red adversaria.
- **CYB-I088** | `INV_LANGUAGE_LEAK`: Lenguaje/Charset embebido mapea axiomáticamente la región sociolingüística de origen.
- **CYB-I089** | `INV_TYPOSQUAT_PREDICT`: Typosquatting se pre-calcula matemáticamente (Distancia de Levenshtein) antes del registro.
- **CYB-I090** | `INV_DEOBFUSCATE_WAR`: Desofuscación es una guerra termodinámica constante entre entropía inyectada y análisis estático.

### Singularidad CYBINT-Física (091-100)
- **CYB-I091** | `INV_KINETIC_IMPACT`: Dominio Cíber rompe la contención lógica causando daños cinéticos físicos (ICS/SCADA).
- **CYB-I092** | `INV_OT_AVAILABILITY`: Entornos OT prefieren correr expuestos a caerse; su axioma es disponibilidad > seguridad.
- **CYB-I093** | `INV_ESPIONAGE_PRECEDENCE`: Preparación CYBINT antecede estructuralmente a cualquier movilización militar física.
- **CYB-I094** | `INV_IOT_BOTNET_VECTOR`: Dispositivos IoT son termodinámicamente indefensos, presa natural de grandes Botnets (Mirai).
- **CYB-I095** | `INV_PHYSICAL_BYPASS`: Acceso físico de capa 1 es un bypass inmutable de cualquier firewall L7.
- **CYB-I096** | `INV_SIGINT_CYBINT_NEXUS`: Intercepción RF alimenta directamente los nodos de Caza Cibernética.
- **CYB-I097** | `INV_DRONE_SURFACE`: Drones convierten el espacio aéreo en una VLAN extendida vulnerable a hacking.
- **CYB-I098** | `INV_AI_ACCELERATION`: Redes Neuronales acortan el tiempo TTP de adaptación a casi cero (Singularidad Defensiva).
- **CYB-I099** | `INV_DISINFO_REALITY`: Inyecciones Cibernéticas de desinformación reescriben los grafos de creencia física social.
- **CYB-I100** | `INV_ABSOLUTE_ASYMMETRY`: El defensor cubre N vectores; el atacante explota O(1). Cero Anergía es la única métrica de supervivencia.

---

## 🚀 PARTE III: 3 HIGH-EXERGY USE CASES

### Caso 1: Desmantelamiento de Infraestructura RaaS (Ransomware as a Service)
**Vector:** Pivotaje de Dominio y Análisis de Certificados (El adversario es perezoso).
1. **Ingesta:** El SOC detecta un beaconing hacia `update-telemetry[.]com`.
2. **CYB-P002 (OP_PDNS_RESOLVE):** Se identifica que la IP del dominio alojaba previamente `secure-login-portal[.]net`.
3. **CYB-P003 (OP_JARM_FINGERPRINT):** Se escanea la IP. El hash JARM coincide con la firma criptográfica del servidor C2 "Cobalt Strike" por defecto.
4. **CYB-I003 (INV_JARM_COMPARTMENT):** Usando Shodan/Censys, se buscan todas las IPs globales con ese hash JARM y el mismo certificado autofirmado, identificando 45 servidores inactivos del mismo grupo APT antes de que se usen.

### Caso 2: Caza de Amenazas (Threat Hunting) por Comportamiento (Living off the Land)
**Vector:** Análisis de TTPs vs Hashes (Ignorando la Pirámide del Dolor baja).
1. **Hipótesis (CYB-I022 - INV_LEAST_EFFORT):** El atacante usará herramientas nativas de Windows para evadir EDR.
2. **CYB-P066 (OP_SPLUNK_QUERY):** Se programa el SIEM para buscar ejecuciones de `certutil.exe` o `bitsadmin.exe` con argumentos de descarga HTTP (e.g., `-urlcache -split -f`).
3. **Correlación (CYB-P057):** Se cruza la ejecución del proceso con conexiones salientes en el firewall hacia ASNs conocidos por alojar bulletproof hosting.
4. **Resultado:** Detección de una intrusión Fileless en Etapa 2, saltándose las firmas de antivirus que nunca detectaron un binario malicioso.

### Caso 3: Atribución Temprana mediante Análisis OPSEC Fail
**Vector:** OSINT y Metadatos cruzando la barrera física.
1. **Colección:** Un analista extrae un documento de phishing droppeado en la red.
2. **CYB-P006 (OP_EXIF_STRIP):** Se extraen los metadatos del PDF malicioso. El `Author` es un alias cirílico y la zona horaria del documento es `UTC+3`.
3. **CYB-P038 / CYB-P035 (OP_FOCA_METADATA / OP_ALIAS_CORRELATE):** Se busca el alias en foros de la Dark Web (Exploit.in). Se encuentra un handle idéntico que publicó un script en Python hace 3 años.
4. **CYB-I086 (INV_VT_BETRAYAL):** Se busca el hash del script de hace 3 años en VirusTotal (CYB-P051), el cual tiene comentarios de la comunidad que asocian ese script a las fases iniciales del grupo *Sandworm*. Se mapea la intención y se ajustan las defensas a los TTPs conocidos del grupo.
