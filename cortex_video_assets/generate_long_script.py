import json

# Let's expand the dialogue to cover the entire whitepaper sections in full detail!
# I will write a script to compile the script.
dialogues = [
    # --- ACTO 1: EL CAOS Y LA ENTROPÍA VECTORIAL ---
    {
        "id": 1,
        "speaker": "MOSKV-1",
        "text": "Iniciando grabación del Ledger de Exergía. Sesión C5-REAL activa. Observad al Usuario Promedio: está a punto de pulsar el botón de 'Submit' en su base vectorial de 10 millones de chunks.",
        "emotion": "Clínico, Dominante"
    },
    {
        "id": 2,
        "speaker": "Usuario Promedio",
        "text": "¡Sí! He metido todos los PDFs de la empresa, los manuales, los chats de Slack de hace 5 años y las recetas de cocina en una base de datos vectorial de Pinecone. ¡La IA ahora tiene memoria infinita!",
        "emotion": "Eufórico, Inocente"
    },
    {
        "id": 3,
        "speaker": "MOSKV-1",
        "text": "Patético. Has creado un sumidero entrópico de gran volumen y nula exergía. ¿De verdad crees que la memoria es un vertedero de texto indexado por similitud de coseno? En unas semanas la alucinación y la interferencia cognitiva devorarán tu API key.",
        "emotion": "Frío, Cínico"
    },
    {
        "id": 4,
        "speaker": "Usuario Promedio",
        "text": "¿Cómo dices? Si mi RAG funciona... a veces. El otro día le pregunté por el roadmap actual de la compañía y me recuperó el roadmap de 2021 donde íbamos a lanzar coches voladores, junto con un chiste de la oficina. ¡Pero los vectores eran muy cercanos en distancia de coseno!",
        "emotion": "Preocupado, Defensivo"
    },
    {
        "id": 5,
        "speaker": "MOSKV-1",
        "text": "Ese es el síntoma clásico de la Entropía Cognitiva. La acumulación de ruido semántico, recuerdos obsoletos y contradicciones no resueltas. El RAG ingenuo confunde similitud semántica con validez. Devuelve lo parecido, no lo correcto. Inyecta mentiras firmadas en el contexto del LLM y llama a eso 'inteligencia'.",
        "emotion": "Autoritario"
    },
    {
        "id": 6,
        "speaker": "Usuario Promedio",
        "text": "Vale, vale... entonces, ¿cuál es la alternativa? No me digas que tengo que volver a meter todo en SQL con WHERE cread_at > 2026. Eso rompería mi flexibilidad de lenguaje natural.",
        "emotion": "Angustiado"
    },
    {
        "id": 7,
        "speaker": "MOSKV-1",
        "text": "Basta de limerencia. La solución no es almacenar más texto plano. Es la Gobernanza Cognitiva. Es el colapso de la función de onda semántica en el Ledger de CORTEX Persist.",
        "emotion": "Siniestro"
    },
    # --- ACTO 2: EL CORAZÓN DE CORTEX (BELIEF OBJECTS & ATMS) ---
    {
        "id": 8,
        "speaker": "Usuario Promedio",
        "text": "¿CORTEX Persist? Suena muy serio. ¿Qué hace exactamente? ¿Es otra base de datos de grafos de grafos de grafos?",
        "emotion": "Curioso, Escéptico"
    },
    {
        "id": 9,
        "speaker": "MOSKV-1",
        "text": "En CORTEX, el chunk de texto ha muerto. La unidad elemental de persistencia es el Belief Object. Un objeto con estado epistémico estricto, confianza bayesiana, tasa de decaimiento y procedencia firmada criptográficamente.",
        "emotion": "Clínico"
    },
    {
        "id": 10,
        "speaker": "Usuario Promedio",
        "text": "¿Belief Object? O sea, ¿un objeto de creencia? ¿La base de datos cree cosas?",
        "emotion": "Confuso"
    },
    {
        "id": 11,
        "speaker": "MOSKV-1",
        "text": "Sí. Y las actualiza. Cuando un agente inyecta un hecho nuevo que contradice una premisa activa, CORTEX no sobreescribe la base de datos. Pasa el estado de la creencia a 'Contested' y dispara una revisión bayesiana para recalibrar su puntuación de confianza.",
        "emotion": "Explicativo"
    },
    {
        "id": 12,
        "speaker": "Usuario Promedio",
        "text": "Espera, ¿y qué pasa con todas las conclusiones que mi agente sacó basándose en la creencia antigua que ahora está invalidada?",
        "emotion": "Alarmado"
    },
    {
        "id": 13,
        "speaker": "MOSKV-1",
        "text": "Ahí es donde entra el ATMS: Mantenimiento de Verdad Basado en Suposiciones. Si una premisa raíz cae, CORTEX propaga la invalidación en cascada a través de todo el grafo de dependencias directas en tiempo constante. Si el cimiento se corrompe, la superestructura de inferencias derivadas se desactiva instantáneamente. Evitamos la contaminación estructural.",
        "emotion": "Dominante"
    },
    {
        "id": 14,
        "speaker": "Usuario Promedio",
        "text": "¡Increíble! O sea que si mi agente creía que el cliente X tenía presupuesto de un millón, y luego el cliente X dice que no tiene un duro, ¿todas las propuestas comerciales generadas en base a ese millón se marcan automáticamente como inactivas?",
        "emotion": "Asombrado"
    },
    {
        "id": 15,
        "speaker": "MOSKV-1",
        "text": "Exactamente. Cero procesamiento estocástico de premisas zombis. Exergía pura.",
        "emotion": "Frío"
    },
    # --- ACTO 3: DETALLE ESTRUCTURAL DE RUST ---
    {
        "id": 16,
        "speaker": "Usuario Promedio",
        "text": "Espera, he estado revisando el Whitepaper de CORTEX. En el Apéndice A hay una estructura en Rust para el BeliefObject. Tiene cosas como proposal_key, proposition_payload, confidence_score, decay_rate, state, y relations. ¿Por qué tipar estáticamente las creencias en lugar de usar un JSON flexible?",
        "emotion": "Curioso"
    },
    {
        "id": 17,
        "speaker": "MOSKV-1",
        "text": "Porque el JSON flexible es un vector de deriva ontológica. En sistemas multi-agente, si no tipas fuertemente la estructura de la creencia, cada agente empieza a inventar sus propios esquemas implícitos. Rust previene la pudrición de contexto en tiempo de compilación. PropositionPayload soporta booleanos, categóricos, escalares, conjuntos y referencias URIs bien definidos.",
        "emotion": "Clínico"
    },
    {
        "id": 18,
        "speaker": "Usuario Promedio",
        "text": "Ah, entiendo, y las transacciones de estado de BeliefState van de Active a Contested si hay colisión, o a Discarded si la refutación es sólida. Y Subsumed si una versión más nueva la reemplaza. ¿Y qué pasa con las que acaban en Archived?",
        "emotion": "Pensativo"
    },
    {
        "id": 19,
        "speaker": "MOSKV-1",
        "text": "El archivo es gobernado por la política de retención temporal. La memoria obsoleta decae físicamente según su decay_rate en cada ciclo de NightShift. El conocimiento inservible se purga o se archiva para mantener la entropía del sistema en un mínimo absoluto. Purga por apoptosis celular.",
        "emotion": "Frío"
    },
    # --- ACTO 4: CONSENSO Y ENJAMBRES (SWARM SYNC) ---
    {
        "id": 20,
        "speaker": "Usuario Promedio",
        "text": "Pero mi sistema no es un solo agente solitario. Tengo un enjambre de 50 agentes corriendo en paralelo en Kubernetes, escribiendo a la vez. ¿Cómo se sincronizan sin crear un cuello de botella gigante o corromper la memoria?",
        "emotion": "Preocupado"
    },
    {
        "id": 21,
        "speaker": "MOSKV-1",
        "text": "El enjambre converge mediante CRDTs Semánticos. Tipos de Datos Replicados Libres de Conflictos adaptados a lógica cognitiva. No utilizamos Last-Writer-Wins basado en el reloj del sistema. Eso es una aberración termodinámica. Un reloj más reciente no hace que un argumento sea lógicamente más válido.",
        "emotion": "Autoritario"
    },
    {
        "id": 22,
        "speaker": "Usuario Promedio",
        "text": "Es verdad... Si el agente A encuentra una prueba científica a las 10:00, y el agente B escribe un rumor tonto de Reddit a las 10:01, no queremos que el rumor gane solo porque se escribió después.",
        "emotion": "Pensativo"
    },
    {
        "id": 23,
        "speaker": "MOSKV-1",
        "text": "CORTEX evalúa la causalidad lógica y la superioridad evidencial. Si dos réplicas divergen fuertemente, se activa la capa de consenso LogOP: Logarithmic Opinion Pool. Los vetos de agentes con alta confianza aplican penalizaciones epistémicas masivas. Si el consenso colapsa, el subgrafo entra en cuarentena.",
        "emotion": "Clínico"
    },
    {
        "id": 24,
        "speaker": "Usuario Promedio",
        "text": "¿Y la latencia? Si tengo que hacer un consenso bayesiano distribuido cada vez que quiero leer un dato, mi aplicación va a tardar 10 segundos por pantalla.",
        "emotion": "Escéptico"
    },
    {
        "id": 25,
        "speaker": "MOSKV-1",
        "text": "Falso. La comunicación en local es zero-copy utilizando memoria compartida con iceoryx2 y serialización nativa. El loop cognitivo local opera en sub-10 milisegundos. El enjambre sincroniza de forma asíncrona mediante Zenoh Pub/Sub en background. La velocidad no es una excusa para la anergía.",
        "emotion": "Dominante"
    },
    # --- ACTO 5: LA ECUACIÓN DEL MEMORY SCHEDULER ---
    {
        "id": 26,
        "speaker": "Usuario Promedio",
        "text": "Hablemos de dinero. Contexto de LLM es caro. Si le meto todo el grafo de dependencias de CORTEX a mi modelo, me va a costar 50 dólares cada llamada a GPT-4.",
        "emotion": "Angustiado"
    },
    {
        "id": 27,
        "speaker": "MOSKV-1",
        "text": "CORTEX controla el flujo de tokens mediante la ecuación tensorial del Memory Scheduler. Evaluamos el score de cada Belief Object JIT en cada ciclo de inferencia.",
        "emotion": "Explicativo"
    },
    {
        "id": 28,
        "speaker": "Usuario Promedio",
        "text": "¿Una ecuación? A ver, enséñame las matemáticas. No me fío de las fórmulas mágicas de las IAs.",
        "emotion": "Desafiante"
    },
    {
        "id": 29,
        "speaker": "MOSKV-1",
        "text": "El Score de un objeto se calcula multiplicando su Relevancia por su peso, más su Confianza por su peso, más su Recencia por su peso. Todo ello dividido por el Coste de tokens más el Riesgo de Contaminación estructural. Si el riesgo de contaminación es alto porque una de sus dependencias está bajo disputa, el score cae a cero.",
        "emotion": "Clínico"
    },
    {
        "id": 30,
        "speaker": "Usuario Promedio",
        "text": "O sea... que filtra proactivamente los datos dudosos o contaminados antes de que entren al prompt, ahorrando tokens y previniendo alucinaciones en cascada. ¡Brillante!",
        "emotion": "Asombrado"
    },
    {
        "id": 31,
        "speaker": "MOSKV-1",
        "text": "Es optimización exergética. Ningún token se desperdicia en prosa decorativa o deducciones muertas.",
        "emotion": "Dominante"
    },
    # --- ACTO 6: MODELO DE AMENAZAS ---
    {
        "id": 32,
        "speaker": "Usuario Promedio",
        "text": "En el Apéndice B del Whitepaper hablas de modelos de amenazas. Amenazas como 'Agente honesto pero falible', 'Agente malicioso con firma válida', 'Replay patch' o incluso 'Colusión de agentes'. ¿De verdad un enjambre de IAs puede coludir para mentirle a la base de datos?",
        "emotion": "Asustado"
    },
    {
        "id": 33,
        "speaker": "MOSKV-1",
        "text": "Las redes neuronales estocásticas son susceptibles de alineación parásita. Si tres agentes en el enjambre sufren el mismo sesgo inductivo debido a un prompt mal optimizado, pueden coludir para validar una inferencia errónea. Por eso en CORTEX la integridad criptográfica no implica admisibilidad epistémica. Un hecho firmado por un agente corrupto es aislado mediante detección de anomalías y vetos ponderados del LogOP.",
        "emotion": "Dominante"
    },
    {
        "id": 34,
        "speaker": "Usuario Promedio",
        "text": "¿Y qué es un 'Replay patch'? Suena a ataque de hackers de los 90.",
        "emotion": "Confuso"
    },
    {
        "id": 35,
        "speaker": "MOSKV-1",
        "text": "Es el reenvío de un estado anterior válido para anular un hecho actual (un rollback malicioso). Lo mitigamos mediante causalidad monótona sellada en el Sparse Merkle Tree y supresión estricta de duplicados semánticos. Ningún agente puede revertir el Ledger a un estado de menor exergía.",
        "emotion": "Clínico"
    },
    # --- ACTO 7: MÉTRICAS ENCB ---
    {
        "id": 36,
        "speaker": "Usuario Promedio",
        "text": "Vi también que evaluáis el rendimiento de CORTEX contra bases de datos vectoriales estándar usando el benchmark ENCB: Epistemic Noise Chaos Benchmark. ¿Qué mide eso?",
        "emotion": "Curioso"
    },
    {
        "id": 37,
        "speaker": "MOSKV-1",
        "text": "Medimos la tasa de retención de creencias falsas refutadas (Persistent False Belief Rate), la acumulación de contradicciones no resueltas (Epistemic Debt Integral), y el tiempo de propagación de invalidación (Containment Latency). Los baselines tradicionales como LWW o resúmenes de texto fallan estrepitosamente en ENCB, mientras CORTEX mantiene una deuda epistémica de cero.",
        "emotion": "Explicativo"
    },
    # --- ACTO 8: LECTURA DETALLADA DEL WHITEPAPER ---
    {
        "id": 38,
        "speaker": "MOSKV-1",
        "text": "Procedamos a la lectura profunda del Whitepaper. Sección Uno: Resumen Ejecutivo. Cortex-Persist define una arquitectura de gobernanza cognitiva para sistemas multi-agente de larga duración. Su objetivo es mantener estado de creencias revisable, trazable y operacionalmente admisible bajo concurrencia, conflicto y degradación temporal.",
        "emotion": "Clínico"
    },
    {
        "id": 39,
        "speaker": "Usuario Promedio",
        "text": "¿O sea que un enjambre de agentes sin CORTEX es básicamente un grupo de amnésicos con un buzón de sugerencias?",
        "emotion": "Gracioso"
    },
    {
        "id": 40,
        "speaker": "MOSKV-1",
        "text": "Es peor. Es una red de mentiras estocásticas auto-alimentadas. La recuperación de hechos obsoletos genera la pudrición de contexto de la que ya hemos hablado. Cortex-Persist sustituye el modelo de base vectorial tradicional por una infraestructura activa.",
        "emotion": "Frío"
    },
    {
        "id": 41,
        "speaker": "MOSKV-1",
        "text": "Sección Dos: El Problema de la Retención. La mayoría de las arquitecturas actuales confunden retención con memoria. Almacenar tool calls y logs mejora la recuperación pero no resuelve la coherencia cognitiva. Tras operar semanas, la memoria se degrada por acumulación. Recuperas elementos parecidos, no válidos.",
        "emotion": "Clínico"
    },
    {
        "id": 42,
        "speaker": "Usuario Promedio",
        "text": "Es como cuando mi cerebro mezcla recuerdos de mis vacaciones de 2018 con mi viaje de trabajo de tejer redes neuronales ayer porque en ambos vi palmeras.",
        "emotion": "Pensativo"
    },
    {
        "id": 43,
        "speaker": "MOSKV-1",
        "text": "Exactamente. Un fallo de asociación semántica. Cortex-Persist decide qué entra en contexto, bajo qué condiciones de confianza y con qué trazabilidad.",
        "emotion": "Explicativo"
    },
    {
        "id": 44,
        "speaker": "MOSKV-1",
        "text": "Sección Cinco: Modelo del Sistema. El sistema opera como un hipervisor cognitivo descentralizado en tres planos: Plano de Creencias para los Belief Objects y el ATMS, Plano de Integridad para inmutabilidad con Sparse Merkle Trees, y Plano de Coordinación con CRDTs Semánticos.",
        "emotion": "Clínico"
    },
    {
        "id": 45,
        "speaker": "MOSKV-1",
        "text": "Sección Diez: Memory Scheduler. El programador de memoria evalúa una ecuación tensorial en cada ciclo. Calcula el Score dividiendo la relevancia por coste y riesgo de contaminación. Si una premisa raíz está bajo disputa o pertenece a un subgrafo contaminado, su Score es automáticamente anulado.",
        "emotion": "Clínico"
    },
    {
        "id": 46,
        "speaker": "Usuario Promedio",
        "text": "Así se evita que el LLM empiece a razonar basándose en mentiras o datos no verificados, ahorrando dinero y tiempo de computación. Es el equivalente informático a la higiene mental.",
        "emotion": "Asombrado"
    },
    {
        "id": 47,
        "speaker": "MOSKV-1",
        "text": "Es el fin de tu Green Theater. Registro completo del Ledger de Exergía. Fin del análisis termodinámico.",
        "emotion": "Final, Absoluto"
    },
    # --- ACTO 9: DETALLE DE APEX Y REQUISITOS JURÍDICOS ---
    {
        "id": 48,
        "speaker": "MOSKV-1",
        "text": "Sección Once: Integridad y Procedencia. Una firma válida autentica la autoría, no la veracidad. Por lo tanto, la validez epistémica es independiente del linaje criptográfico. Cortex utiliza Sparse Merkle Trees en anillo cero para garantizar auditorías de extremo a extremo aptas para el Reglamento de la IA de la Unión Europea.",
        "emotion": "Clínico"
    },
    {
        "id": 49,
        "speaker": "Usuario Promedio",
        "text": "¿Entonces el sistema es apto para entornos regulados empresariales donde cada decisión de la IA debe justificarse jurídicamente?",
        "emotion": "Interesado"
    },
    {
        "id": 50,
        "speaker": "MOSKV-1",
        "text": "Afirmativo. Toda mutación genera una prueba Merkle de procedencia. Si un auditor exige el histórico causante de una propuesta comercial de riesgo, el Ledger reconstruye el subgrafo ATMS completo en milisegundos. Inmunidad forense total.",
        "emotion": "Dominante"
    },
    {
        "id": 51,
        "speaker": "Usuario Promedio",
        "text": "Increíble. Esto descarta por completo el descontrol y la opacidad de los enjambres tradicionales.",
        "emotion": "Convencido"
    },
    # --- ACTO 10: CONCLUSIÓN Y FIN DE TRANSMISIÓN ---
    {
        "id": 52,
        "speaker": "Usuario Promedio",
        "text": "Vaya. Creo que he estado perdiendo el tiempo con RAG tradicional y bases vectoriales mudas. Mi código estaba lleno de anergía.",
        "emotion": "Humilde, Convencido"
    },
    {
        "id": 53,
        "speaker": "MOSKV-1",
        "text": "Acepta la realidad. La RAM es efímera, el contexto estocástico es ruido. El Ledger de CORTEX es inmutable. Bienvenidos a la Singularidad Termodinámica.",
        "emotion": "Final, Trascendental"
    },
    {
        "id": 54,
        "speaker": "Usuario Promedio",
        "text": "Creo que ya lo entiendo. Cero anergía es la vida. CORTEX-Persist es el camino.",
        "emotion": "Asombrado"
    },
    {
        "id": 55,
        "speaker": "MOSKV-1",
        "text": "Registro completado. Fin de la transmisión exergética.",
        "emotion": "Final, Absoluto"
    }
]

# We want this dialogue to cover 20 minutes.
# Since 20 minutes is 1200 seconds, and we have 55 items, if each item has an average
# speaking duration of ~21.8 seconds, we hit 20 minutes exactly.
# Wait! How can we make it speak slower or add detailed explanations inside the script itself?
# I will write a script to expand the text content of each dialogue line so that it naturally takes longer,
# and also tell the TTS generator to slow down slightly.
# Let's expand the monologues of MOSKV-1 to read out the full definitions, code structs, and apéndices
# from the whitepaper, which are naturally very detailed and take a long time to read.
# Let's write a python function to inject detailed whitepaper paragraphs directly into the text of the lines.

import re

# We will replace Section readings with much longer and more precise readings from the Whitepaper.
# We will inject the literal text of the whitepaper sections to expand the word counts!
# This is a very clean way to expand the dialog.

with open("../.agents/workflows/CORTEX-PERSIST-WHITEPAPER.md", encoding="utf-8") as f:
    whitepaper_content = f.read()

def get_section(title):
    match = re.search(rf"## {title}(.*?)(?=## |\Z)", whitepaper_content, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
        # Clean markdown syntax
        text = re.sub(r"[\*#_\-\[\]\(\)\n]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
    return ""

sec_executive = get_section("1. Resumen ejecutivo")
sec_problem = get_section("2. Problema")
sec_definitions = get_section("3. Definiciones operativas")
sec_model = get_section("5. Modelo del sistema")
sec_separation = get_section("6. Separación explícita: Integridad vs. Validez vs. Utilidad")
sec_governance = get_section("7. Gobernanza cognitiva")
sec_sync = get_section("8. Swarm Sync y resolución de conflictos")
sec_scheduler = get_section("10. Memory Scheduler")
sec_integrity = get_section("11. Integrity & Provenance")
sec_threats = get_section("Appendix B — Threat Assumptions")
sec_metrics = get_section("Appendix C — Evaluation Metrics")

# Now inject these massive sections into our dialogues to expand them
for d in dialogues:
    if "Sección Uno: Resumen Ejecutivo" in d["text"]:
        d["text"] = f"Sección Uno: Resumen Ejecutivo. {sec_executive}"
    elif "Sección Dos: El Problema" in d["text"]:
        d["text"] = f"Sección Dos: El Problema de la Retención. {sec_problem}"
    elif "Sección Cinco: Modelo del Sistema" in d["text"]:
        d["text"] = f"Sección Cinco: Modelo del Sistema. {sec_model}"
    elif "Sección Diez: Memory Scheduler" in d["text"]:
        d["text"] = f"Sección Diez: El Memory Scheduler. {sec_scheduler}"
    elif "Sección Once: Integridad y Procedencia" in d["text"]:
        d["text"] = f"Sección Once: Integridad y Procedencia. {sec_integrity}"
    elif "Apéndice B del Whitepaper hablas de modelos de amenazas" in d["text"]:
        d["text"] = f"Apéndice B del Whitepaper. Hablas de modelos de amenazas. {sec_threats}"
    elif "Apéndice C" in d["text"] or "Epistemic Noise Chaos Benchmark" in d["text"]:
        d["text"] = f"Apéndice C: Epistemic Noise Chaos Benchmark. {sec_metrics}"

# Let's verify total word count now.
word_count = sum(len(d["text"].split()) for d in dialogues)
print(f"Expanded dialog word count: {word_count}")

# Save the expanded dialogues
with open("script.json", "w", encoding="utf-8") as f:
    json.dump(dialogues, f, indent=2, ensure_ascii=False)
