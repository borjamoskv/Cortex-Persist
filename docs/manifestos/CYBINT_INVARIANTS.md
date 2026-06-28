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
`CYB-I001` La infraestructura es costosa; los atacantes siempre la reutilizan.
`CYB-I002` El pDNS no miente; el historial de resolución sobrevive a la eliminación del registro.
`CYB-I003` Los certificados SSL compartimentan el ruido; firmas únicas (JARM) delatan el backend.
`CYB-I004` Los dominios generados por algoritmos (DGA) tienen alta entropía pero patrones matemáticos predecibles.
`CYB-I005` Los atacantes cometen errores de configuración (OPSEC fails) al desplegar servidores C2.
`CYB-I006` Fast-Flux oculta la IP, pero revela la red de bots subyacente.
`CYB-I007` El uso de proxies comerciales (VPNs/VPS) anonimiza, pero agrupa a los atacantes en ASNs específicos.
`CYB-I008` Los puertos inusuales (ej. 4444) son firmas de herramientas por defecto.
`CYB-I009` La vida útil de un dominio C2 es inversamente proporcional a su exposición.
`CYB-I010` El beaconing tiene jitter; la ausencia total de jitter delata a un novato o un script básico.

### Artefactos y Malware (011-020)
`CYB-I011` Los hashes (MD5/SHA256) son la métrica más frágil de la inteligencia (Pirámide del Dolor).
`CYB-I012` El fuzzy hashing (SSDeep) expone la evolución del código, no solo la identidad del archivo.
`CYB-I013` Las cadenas de texto (strings) en binarios a menudo revelan rutas de compilación y nombres de usuario.
`CYB-I014` Los packers ocultan el código, pero el packer mismo es una firma identificable.
`CYB-I015` Las marcas de tiempo de compilación (Timestamps) pueden ser falsificadas, pero a menudo se olvidan.
`CYB-I016` Los Mutex previenen la doble infección, pero sirven como un IoC de alta fidelidad.
`CYB-I017` Las importaciones de API (IAT) revelan las intenciones del malware antes de la ejecución.
`CYB-I018` El Rich Header en binarios PE identifica de forma única el entorno de compilación de Windows.
`CYB-I019` La entropía alta en una sección de datos sugiere cifrado o compresión (cargas útiles ocultas).
`CYB-I020` El malware sin archivos (Fileless) reside en la memoria, dejando rastros en los procesos de volcado.

### Comportamiento del Adversario (021-030)
`CYB-I021` Los TTPs (Tácticas, Técnicas y Procedimientos) son el indicador más difícil de cambiar para un atacante.
`CYB-I022` Los atacantes siguen la ley del menor esfuerzo; usan herramientas integradas (Living off the Land) cuando es posible.
`CYB-I023` El espionaje busca persistencia; el cibercrimen busca monetización rápida.
`CYB-I024` Los grupos APT tienen horarios de trabajo; sus commits y ataques siguen husos horarios y días festivos.
`CYB-I025` La atribución definitiva es un mito; la atribución basada en la confianza (Confidence Level) es la realidad.
`CYB-I026` Las falsas banderas (False Flags) son comunes para desviar la atribución a naciones rivales.
`CYB-I027` El Modelo Diamante requiere al menos dos vértices para proporcionar inteligencia procesable.
`CYB-I028` Los actores de amenazas evolucionan sus TTPs en respuesta a la publicación de reportes de inteligencia.
`CYB-I029` El Ransomware as a Service (RaaS) separa al desarrollador (capability) del afiliado (adversary).
`CYB-I030` El acceso inicial se mercantiliza (Initial Access Brokers), creando cadenas de suministro criminales.

### Inteligencia y Datos (031-040)
`CYB-I031` Un IoC sin contexto no es inteligencia, es un bloqueador de firewall.
`CYB-I032` La inteligencia perece; un IoC de hace un año probablemente es un falso positivo hoy.
`CYB-I033` El enriquecimiento de datos reduce la entropía analítica.
`CYB-I034` La correlación de eventos dispares revela la campaña subyacente.
`CYB-I035` Los foros de la Dark Web son ecosistemas de confianza; la reputación es la moneda de cambio.
`CYB-I036` Las filtraciones de datos (Data Leaks) son retrospectivas; el acceso inicial ocurrió meses antes.
`CYB-I037` Las bases de datos de Whois históricas son fundamentales para rastrear la evolución de la infraestructura.
`CYB-I038` El Traffic Light Protocol (TLP) es un pacto de confianza humano, no una medida de seguridad técnica.
`CYB-I039` STIX/TAXII son estándares sintácticos, pero la semántica requiere intervención analítica.
`CYB-I040` Más datos no significa más inteligencia; el ruido oscurece la señal.

### Detección y Respuesta (041-050)
`CYB-I041` La detección perfecta no existe; la resiliencia asume el compromiso.
`CYB-I042` Las reglas YARA buscan cadenas; las reglas Sigma buscan comportamientos.
`CYB-I043` El Threat Hunting asume que los controles preventivos ya han fallado.
`CYB-I044` Los falsos positivos fatigan a los analistas; la alta fidelidad es prioritaria.
`CYB-I045` El tiempo medio de detección (MTTD) mide la eficacia de la inteligencia, no de los firewalls.
`CYB-I046` Las alertas deben tener contexto accionable o ser suprimidas.
`CYB-I047` La caza de amenazas basada en hipótesis es más efectiva que la búsqueda a ciegas de IoCs.
`CYB-I048` Los honeypots generan inteligencia de alta fidelidad con cero falsos positivos (todo tráfico es anómalo).
`CYB-I049` El aislamiento de red es una medida de contención, no de remediación.
`CYB-I050` Los playbooks de incidentes deben ser actualizados con la inteligencia táctica más reciente.

### OSINT y Reconocimiento (051-060)
`CYB-I051` Lo que se publica en internet no se puede borrar de forma fiable (Wayback Machine).
`CYB-I052` Los metadatos de los documentos (EXIF) a menudo comprometen el OPSEC físico del atacante.
`CYB-I053` Las redes sociales son vectores de ingeniería social de alta efectividad.
`CYB-I054` Shodan no ataca; Shodan revela la negligencia de la configuración.
`CYB-I055` La resolución pasiva de DNS permite reconstruir grafos de infraestructura sin tocar el objetivo.
`CYB-I056` Las filtraciones de repositorios de código exponen secretos, no solo propiedad intelectual.
`CYB-I057` Los foros de hackers revelan la demanda del mercado de vulnerabilidades (0-days).
`CYB-I058` Las relaciones en LinkedIn mapean la jerarquía objetivo para campañas de Spear Phishing.
`CYB-I059` El rastreo de billeteras cripto sigue el flujo del dinero (Ransomware), a menudo rompiendo el OPSEC.
`CYB-I060` La inteligencia de fuentes abiertas es el 80% del perfilado inicial de un adversario.

### Vulnerabilidades y Exploits (061-070)
`CYB-I061` Un CVE sin un exploit público (PoC) es un riesgo teórico; con PoC, es una crisis inminente.
`CYB-I062` Los atacantes priorizan la explotación de VPNs y firewalls (borde de la red).
`CYB-I063` Las vulnerabilidades de Día Cero (0-day) son caras; los atacantes prefieren Días N (N-days) no parchados.
`CYB-I064` La gestión de parches siempre va rezagada respecto al desarrollo de exploits.
`CYB-I065` Las vulnerabilidades en la cadena de suministro (Supply Chain) amplifican exponencialmente el radio de explosión.
`CYB-I066` El análisis de parches (Patch Diffing) revela la vulnerabilidad subyacente que fue corregida.
`CYB-I067` La explotación requiere precisión de memoria (ASLR/DEP dificultan, pero no imposibilitan).
`CYB-I068` Los exploits se mercantilizan rápidamente y se integran en frameworks automatizados (Metasploit, Cobalt Strike).
`CYB-I069` La configuración predeterminada insegura es más explotada que los fallos de código complejos.
`CYB-I070` El escaneo masivo de vulnerabilidades comienza minutos después de la divulgación pública de un PoC.

### Gobernanza y Estrategia (071-080)
`CYB-I071` La inteligencia debe responder a un Requisito Prioritario de Inteligencia (PIR) o es un desperdicio de exergía.
`CYB-I072` La inteligencia no procesable (Actionable Intel) es simplemente noticias cibernéticas.
`CYB-I073` La retroalimentación (Feedback) del SOC a los analistas de inteligencia cierra el ciclo y refina las alertas.
`CYB-I074` El intercambio de inteligencia (Sharing) fortalece la defensa colectiva, pero requiere confianza.
`CYB-I075` La automatización es obligatoria para el procesamiento de datos; el análisis requiere cognición humana (o IA avanzada).
`CYB-I076` La inteligencia táctica previene incidentes; la inteligencia estratégica guía la inversión en seguridad.
`CYB-I077` El sesgo de confirmación es el mayor enemigo del analista de inteligencia.
`CYB-I078` La confianza en la fuente (Reliability) y en la información (Credibility) deben evaluarse por separado.
`CYB-I079` La diseminación oportuna de inteligencia imperfecta es mejor que la inteligencia perfecta entregada tarde.
`CYB-I080` El programa de inteligencia madura cuando pasa de consumir feeds a producir inteligencia original.

### Criptografía y OPSEC (081-090)
`CYB-I081` La criptografía mal implementada es peor que la falta de criptografía (falsa sensación de seguridad).
`CYB-I082` Los atacantes usan cifrado simétrico para los datos y asimétrico para proteger las claves (Ransomware).
`CYB-I083` El análisis de tráfico cifrado infiere intenciones mediante el tamaño, la frecuencia y el tiempo de los paquetes.
`CYB-I084` La reutilización de código (Code Reuse) a través de campañas de malware es inevitable debido a la economía del desarrollo.
`CYB-I085` El OPSEC perfecto es imposible a largo plazo; la fatiga del atacante genera errores.
`CYB-I086` Los atacantes a menudo prueban su propio malware contra VirusTotal, revelando sus campañas antes de lanzarlas.
`CYB-I087` Las cuentas de correo de recuperación y la infraestructura compartida exponen redes enteras de actores.
`CYB-I088` El uso de idiomas y teclados específicos en el código fuente o metadatos acota la geolocalización.
`CYB-I089` Los atacantes registran dominios parecidos (Typosquatting) con meses de antelación a una campaña.
`CYB-I090` La desofuscación automatizada es una carrera armamentística continua contra nuevos empacadores.

### Singularidad CYBINT-Física (091-100)
`CYB-I091` El daño cibernético tiene consecuencias cinéticas (ICS/SCADA).
`CYB-I092` Las redes OT (Tecnología Operativa) priorizan la disponibilidad sobre la confidencialidad, haciéndolas frágiles.
`CYB-I093` El espionaje cibernético precede inevitablemente al conflicto geopolítico físico.
`CYB-I094` Los dispositivos IoT son la cabeza de playa preferida para la formación masiva de botnets (Mirai).
`CYB-I095` La seguridad física y la ciberseguridad son el mismo dominio; un USB en el estacionamiento elude los firewalls.
`CYB-I096` La intercepción de RF (SIGINT) alimenta directamente los grafos de amenazas cibernéticas (CYBINT).
`CYB-I097` Los drones y vehículos autónomos amplían la superficie de ataque cibernético al espacio aéreo y terrestre.
`CYB-I098` La inteligencia artificial acelera la velocidad de adaptación de los TTPs, colapsando el tiempo de respuesta.
`CYB-I099` Las campañas de desinformación cibernética alteran la percepción de la realidad física de la sociedad.
`CYB-I100` **La asimetría es absoluta:** El defensor debe proteger todo el perímetro; el atacante solo necesita una vulnerabilidad (Cero Anergía).

---

## 🚀 PARTE III: 3 HIGH-EXERGY USE CASES

### Caso 1: Desmantelamiento de Infraestructura RaaS (Ransomware as a Service)
**Vector:** Pivotaje de Dominio y Análisis de Certificados (El adversario es perezoso).
1. **Ingesta:** El SOC detecta un beaconing hacia `update-telemetry[.]com`.
2. **CYB-P002 (OP_PDNS_RESOLVE):** Se identifica que la IP del dominio alojaba previamente `secure-login-portal[.]net`.
3. **CYB-P003 (OP_JARM_FINGERPRINT):** Se escanea la IP. El hash JARM coincide con la firma criptográfica del servidor C2 "Cobalt Strike" por defecto.
4. **CYB-I003 (Invariante):** Usando Shodan/Censys, se buscan todas las IPs globales con ese hash JARM y el mismo certificado autofirmado, identificando 45 servidores inactivos del mismo grupo APT antes de que se usen.

### Caso 2: Caza de Amenazas (Threat Hunting) por Comportamiento (Living off the Land)
**Vector:** Análisis de TTPs vs Hashes (Ignorando la Pirámide del Dolor baja).
1. **Hipótesis (CYB-I022):** El atacante usará herramientas nativas de Windows para evadir EDR.
2. **CYB-P066 (OP_SPLUNK_QUERY):** Se programa el SIEM para buscar ejecuciones de `certutil.exe` o `bitsadmin.exe` con argumentos de descarga HTTP (e.g., `-urlcache -split -f`).
3. **Correlación (CYB-P057):** Se cruza la ejecución del proceso con conexiones salientes en el firewall hacia ASNs conocidos por alojar bulletproof hosting.
4. **Resultado:** Detección de una intrusión Fileless en Etapa 2, saltándose las firmas de antivirus que nunca detectaron un binario malicioso.

### Caso 3: Atribución Temprana mediante Análisis OPSEC Fail
**Vector:** OSINT y Metadatos cruzando la barrera física.
1. **Colección:** Un analista extrae un documento de phishing droppeado en la red.
2. **CYB-P006 (OP_EXIF_STRIP):** Se extraen los metadatos del PDF malicioso. El `Author` es un alias cirílico y la zona horaria del documento es `UTC+3`.
3. **CYB-P038 / CYB-P035 (OP_FOCA_METADATA / OP_ALIAS_CORRELATE):** Se busca el alias en foros de la Dark Web (Exploit.in). Se encuentra un handle idéntico que publicó un script en Python hace 3 años.
4. **CYB-I086 (Invariante):** Se busca el hash del script de hace 3 años en VirusTotal (CYB-P051), el cual tiene comentarios de la comunidad que asocian ese script a las fases iniciales del grupo *Sandworm*. Se mapea la intención y se ajustan las defensas a los TTPs conocidos del grupo.
