# MATRIZ DE EXTRACCIÓN ONTOLÓGICA (DOMINIOS 1 Y 2)

## 1000 Primitivas — 10 Teorías × 100 Primitivas

### DOMINIO 1: TEORÍA DE CATEGORÍAS (CAT)
### 1.1 Objetos y Morfismos Fundamentales (CAT-001 → CAT-020)
| ID | Primitiva | Definición Formal |
| :--- | :--- | :--- |
| CAT-001 | Functor de Preservación de Estado | Mapeo F: C→D que preserva identidad y composición entre categorías de estado del sistema |
| CAT-002 | Transformación Natural | Mutación η: F⇒G entre functores que conmuta con todos los morfismos sin alterar topología |
| CAT-003 | Límite Categórico | Cono universal terminal: consenso de enjambre como objeto terminal de un diagrama |
| CAT-004 | Colímite Categórico | Cocono universal inicial: fusión de estados divergentes en un estado canónico |
| CAT-005 | Objeto Inicial | ∅-Estado: el estado vacío desde el cual todo worktree se origina (void bootstrap) |
| CAT-006 | Objeto Terminal | 1-Estado: el estado de convergencia al que todo pipeline debe colapsar para ser válido |
| CAT-007 | Morfismo de Identidad | id_A: A→A, la operación nula que certifica que un estado no ha sido alterado (hash check) |
| CAT-008 | Composición Asociativa | (g∘f)∘h = g∘(f∘h): garantía de que el orden de encadenamiento de mutaciones es determinista |
| CAT-009 | Isomorfismo Categórico | f: A→B con inversa g: B→A tal que g∘f=id_A, f∘g=id_B: equivalencia perfecta entre estados |
| CAT-010 | Epimorfismo | Morfismo surjectivo: toda salida del pipeline tiene al menos una entrada causal |
| CAT-011 | Monomorfismo | Morfismo inyectivo: entradas distintas producen estados distintos (no-colisión de hashes) |
| CAT-012 | Endomorfismo | f: A→A no trivial: transformación interna de estado (self-mutation del AST) |
| CAT-013 | Automorfismo | Endomorfismo invertible: transformación reversible de estado (rollback garantizado) |
| CAT-014 | Categoría Opuesta | C^op: inversión de todos los morfismos. Análisis de causalidad reversa (backtracking) |
| CAT-015 | Categoría Producto | C×D: ejecución paralela de dos pipelines con estado combinado |
| CAT-016 | Categoría Coma | (F↓G): espacio de transiciones entre dos functores. Espacio de migraciones de estado |
| CAT-017 | Categoría Slice | C/A: todos los morfismos que apuntan a un objeto A. Dependencias de un módulo |
| CAT-018 | Categoría Coslice | A/C: todos los morfismos que parten de A. Ramificaciones desde un commit |
| CAT-019 | Subcategoría Plena | Inclusión que preserva todos los morfismos entre objetos seleccionados (filtrado sin pérdida) |
| CAT-020 | Subcategoría Ancha | Inclusión que contiene todos los objetos pero restringe morfismos (restricción de permisos) |

### 1.2 Functores y Mapeos (CAT-021 → CAT-040)
| ID | Primitiva | Definición Formal |
| :--- | :--- | :--- |
| CAT-021 | Functor Covariante | F: C→D que preserva dirección de morfismos: mapeo de pipeline que conserva flujo causal |
| CAT-022 | Functor Contravariante | F: C→D^op que invierte dirección: transformación de productor a consumidor |
| CAT-023 | Functor Fiel | F inyectivo en hom-sets: mapeo que no confunde operaciones distintas |
| CAT-024 | Functor Pleno | F surjectivo en hom-sets: mapeo que no pierde operaciones disponibles |
| CAT-025 | Functor Plenamente Fiel | Embedding categórico: inclusión perfecta de un subsistema en otro |
| CAT-026 | Functor de Olvido | U: Struct→Set que descarta estructura: extracción de datos crudos desde estados tipados |
| CAT-027 | Functor Libre | F: Set→Struct adjunto izquierdo al olvido: generación de estructura mínima desde datos crudos |
| CAT-028 | Bifunctor | F: C×D→E: operación que toma dos inputs de categorías distintas (join cross-domain) |
| CAT-029 | Profunctor | P: C^op × D → Set: relación heterogénea entre sistemas (bridge entre tenants) |
| CAT-030 | Functor Representable | Hom(A,−): C→Set: espacio de todas las operaciones posibles desde un estado dado |
| CAT-031 | Functor Hom Interno | [A,B]: exponencial categórico: espacio de funciones/lambdas entre tipos |
| CAT-032 | Functor Diagonal | Δ: C→C×C: duplicación de estado para validación paralela (N=3 quorum) |
| CAT-033 | Functor Constante | Δ_A: siempre retorna A: estado invariante como baseline de comparación |
| CAT-034 | Functor Potencia | P: C→C que mapea A al objeto de sus subobjetos: generación de espacio de configuraciones |
| CAT-035 | Equivalencia de Categorías | F: C→D con cuasi-inversa: dos sistemas son computacionalmente equivalentes |
| CAT-036 | Adjunción Libre-Olvidadizo | F⊣U: par fundamental generación-extracción. Bootstrap-Teardown de contexto |
| CAT-037 | Unidad de Adjunción | η: Id_C → U∘F: inyección de dato crudo en su envolvente estructural |
| CAT-038 | Counidad de Adjunción | ε: F∘U → Id_D: evaluación/colapso de estructura a resultado concreto |
| CAT-039 | Adjunción de Galois | Conexión entre retículos: mapeo entre jerarquías de permisos/restricciones |
| CAT-040 | Functor Nervio | N: Cat→sSet: serialización de una categoría en su representación simplicial (log chain) |

### 1.3 Estructuras Universales (CAT-041 → CAT-060)
| ID | Primitiva | Definición Formal |
| :--- | :--- | :--- |
| CAT-041 | Producto Categórico | A×B con proyecciones π₁,π₂: estado compuesto con acceso a componentes (struct fields) |
| CAT-042 | Coproducto | A⊔B con inyecciones ι₁,ι₂: unión disjunta de estados (tagged union / enum) |
| CAT-043 | Ecualizador | Eq(f,g): subobjeto donde f=g: filtro de estados que satisfacen invariante |
| CAT-044 | Coecualizador | Coeq(f,g): cociente que identifica outputs iguales: deduplicación semántica |
| CAT-045 | Pullback | A ×_C B: producto fibrado: join de estados sobre un ancestro común (merge de branches) |
| CAT-046 | Pushout | A ⊔_C B: coproducto fibrado: fusión de divergencias desde una base común |
| CAT-047 | Exponencial | B^A: objeto de morfismos de A a B: espacio de todas las transformaciones posibles |
| CAT-048 | Subobjeto Clasificador | Ω con true: 1→Ω: objeto verdad que clasifica todas las subpartes (type predicate) |
| CAT-049 | Objeto Cero | 0 = objeto inicial = terminal: categoría puntuada (null state) |
| CAT-050 | Kernel Categórico | Ker(f) = Eq(f,0): núcleo de una transformación: estados aniquilados por la operación |
| CAT-051 | Cokernel | Coker(f) = Coeq(f,0): cociente por imagen: estados ortogonales a la operación |
| CAT-052 | Imagen Categórica | Im(f): factorización epi-mono: rango efectivo de una transformación |
| CAT-053 | Límite Inverso | lim←: límite de sistema proyectivo: convergencia de refinamientos sucesivos |
| CAT-054 | Límite Directo | lim→: colímite de sistema inductivo: expansión controlada de capacidad |
| CAT-055 | Límite Filtrado | Colímite sobre categoría filtrada: agregación que conmuta con límites finitos |
| CAT-056 | Objeto Compacto | Hom(K,−) conmuta con colímites filtrados: estado finitamente representable |
| CAT-057 | Generador | G tal que Hom(G,−) es fiel: estado desde el cual se puede distinguir todo |
| CAT-058 | Cogenerador | Q tal que Hom(−,Q) es fiel: estado al que se puede proyectar para distinguir |
| CAT-059 | Objeto Proyectivo | P con lifting de epimorfismos: estado que puede acceder a cualquier preimagen |
| CAT-060 | Objeto Inyectivo | I con extensión de monomorfismos: estado que absorbe cualquier inyección parcial |

### 1.4 Monadas y Álgebras (CAT-061 → CAT-080)
| ID | Primitiva | Definición Formal |
| :--- | :--- | :--- |
| CAT-061 | Monada | (T, η, μ): endofunctor con unidad y multiplicación: patrón de encapsulación de efectos |
| CAT-062 | Unidad Monádica | η: Id→T: inyección de valor puro en contexto computacional (wrap) |
| CAT-063 | Multiplicación Monádica | μ: T²→T: aplanamiento de contextos anidados (flatMap / bind) |
| CAT-064 | Álgebra de Monada | α: TA→A: interpretación/evaluación de un programa encapsulado |
| CAT-065 | Categoría de Kleisli | C_T: categoría de morfismos A→TB: composición de operaciones con efectos |
| CAT-066 | Categoría de Eilenberg-Moore | C^T: categoría de T-álgebras: espacio de todas las interpretaciones posibles |
| CAT-067 | Comonada | (D, ε, δ): dual de monada: contexto ambiental y extracción (read environment) |
| CAT-068 | Coextracción | ε: D→Id: extracción de valor desde contexto (unwrap/focus) |
| CAT-069 | Coduplicación | δ: D→D²: duplicación de contexto para inspección (logging sin mutación) |
| CAT-070 | Monada Libre | Free(F): monada generada por un functor: AST sin interpretación fija |
| CAT-071 | Monada Estado | State(S,A) = S→(A,S): computación con estado mutable encapsulado |
| CAT-072 | Monada Reader | Reader(E,A) = E→A: computación con entorno de solo lectura (config injection) |
| CAT-073 | Monada Writer | Writer(W,A) = (A,W): computación con log acumulativo (audit trail) |
| CAT-074 | Monada IO | IO(A): computación con efectos del mundo real (filesystem, network) |
| CAT-075 | Monada Continuación | Cont(R,A) = (A→R)→R: control explícito del flujo futuro (CPS transform) |
| CAT-076 | Transformer Monádico | T∘M: composición de monadas: apilamiento de efectos (error + state + IO) |
| CAT-077 | Distributive Law | λ: ST→TS: ley que permite intercambiar orden de efectos monádicos |
| CAT-078 | Strength Monádica | t: A×TB→T(A×B): capacidad de arrastrar contexto puro a través de efectos |
| CAT-079 | Idempotente Monádico | μ∘η_T = μ∘Tη = id_T: monada cuya aplicación doble no cambia el resultado |
| CAT-080 | Resolución de Monada | Factorización de monada en adjunción F⊣U: descomposición de efecto en generación+interpretación |

### 1.5 Categorías Superiores y Enriquecidas (CAT-081 → CAT-100)
| ID | Primitiva | Definición Formal |
| :--- | :--- | :--- |
| CAT-081 | 2-Categoría | Categoría con 2-morfismos (morfismos entre morfismos): transformaciones de transformaciones |
| CAT-082 | 2-Morfismo | α: f⇒g entre morfismos f,g: A→B: homotopía entre caminos de ejecución |
| CAT-083 | Composición Horizontal | α∗β de 2-morfismos: composición paralela de transformaciones |
| CAT-084 | Composición Vertical | α∘β de 2-morfismos: composición secuencial de transformaciones |
| CAT-085 | Ley de Intercambio | (α∗β)∘(γ∗δ) = (α∘γ)∗(β∘δ): coherencia de composiciones mixtas |
| CAT-086 | ∞-Categoría | Categoría con n-morfismos para todo n: espacio de homotopías sin truncación |
| CAT-087 | Categoría Enriquecida | V-Categoría: hom-objects en V en vez de Set: cuantificación de similaridad (métricas) |
| CAT-088 | Categoría Monoidal | (C, ⊗, I): categoría con producto tensorial: composición paralela de recursos |
| CAT-089 | Categoría Monoidal Simétrica | σ: A⊗B ≅ B⊗A: conmutatividad del paralelismo (orden de ejecución intercambiable) |
| CAT-090 | Categoría Monoidal Cerrada | [A,B] como exponencial respecto a ⊗: funciones de primer orden como recursos |
| CAT-091 | Categoría Trenzada | β: A⊗B → B⊗A con coherencia: intercambio controlado de recursos (no necesariamente simétrico) |
| CAT-092 | Objeto Monoideal | (M, μ: M⊗M→M, η: I→M): objeto con multiplicación y unidad interna (acumulador) |
| CAT-093 | Objeto Comonoideal | (C, δ: C→C⊗C, ε: C→I): objeto con copia y descarte (broadcast/drop) |
| CAT-094 | Topos | Categoría cartesiana cerrada con subobjeto clasificador: universo lógico completo |
| CAT-095 | Topos de Presheaves | [C^op, Set]: funtor de contexto que genera universos locales de estado |
| CAT-096 | Haz (Sheaf) | Presheaf que satisface condición de pegado: estado globalmente consistente desde datos locales |
| CAT-097 | Topología de Grothendieck | J: selección de cubiertas sobre C: definición de qué observaciones son "suficientes" |
| CAT-098 | Kan Extension Izquierda | Lan_K F: mejor aproximación covariante: interpolación óptima de datos incompletos |
| CAT-099 | Kan Extension Derecha | Ran_K F: mejor aproximación contravariante: extrapolación conservadora |
| CAT-100 | Lema de Yoneda | Nat(Hom(A,−), F) ≅ F(A): un objeto es completamente determinado por cómo se relaciona con todos los demás |

### DOMINIO 2: TERMODINÁMICA DE LA COMPUTACIÓN (THD)
### 2.1 Límites Fundamentales (THD-001 → THD-020)
| ID | Primitiva | Definición Formal |
| :--- | :--- | :--- |
| THD-001 | Límite de Landauer | E_min = kT·ln(2) por bit borrado: costo termodinámico irreducible del olvido |
| THD-002 | Exergía Computacional | Energía libre disponible para realizar trabajo útil de transformación en el AST |
| THD-003 | Disipación Estocástica | Energía convertida en calor sin producir trabajo útil: Green Theater / anergía |
| THD-004 | Entropía de Von Neumann | S(ρ) = −Tr(ρ ln ρ): medida de información en estados cuánticos/mixtos del sistema |
| THD-005 | Principio de Carnot Computacional | Eficiencia máxima η = 1 − T_cold/T_hot: límite de conversión información→acción |
| THD-006 | Demonio de Maxwell | Agente que reduce entropía localmente a costa de aumentarla globalmente (sorting) |
| THD-007 | Erasure Tax | Costo total acumulado de borrar estados intermedios durante la ejecución |
| THD-008 | Reversibilidad de Bennett | Computación reversible que evita disipación de Landauer: backtracking sin pérdida |
| THD-009 | Costo de Copia | En computación clásica: copiar es gratis; en termodinámica: copia ≠ gratuita si implica borrado |
| THD-010 | Trabajo de Szilard | W = kT·ln(2): trabajo extractable de un bit de información (motor de un bit) |
| THD-011 | Principio de Equipartición | kT/2 por grado de libertad: distribución base de energía en subsistemas |
| THD-012 | Fluctuación-Disipación | Relación entre ruido térmico y disipación: base del balance señal/ruido en pipelines |
| THD-013 | Irreversibilidad Termodinámica | ΔS_universe ≥ 0: toda ejecución real incrementa entropía global del sistema |
| THD-014 | Energía Libre de Helmholtz | F = U − TS: energía disponible para trabajo a temperatura constante |
| THD-015 | Energía Libre de Gibbs | G = H − TS: potencial para trabajo útil a presión y temperatura constantes |
| THD-016 | Potencial Químico Computacional | μ = ∂G/∂N: costo marginal de añadir un agente/nodo al enjambre |
| THD-017 | Equilibrio Termodinámico | Estado de máxima entropía: sistema sin gradientes explotables (muerte térmica del contexto) |
| THD-018 | Estado Estacionario de No-Equilibrio | Flujo constante de entropía: sistema vivo con disipación continua (NESS) |
| THD-019 | Producción Mínima de Entropía | Principio de Prigogine: sistemas cerca del equilibrio minimizan producción de entropía |
| THD-020 | Máxima Producción de Entropía | Principio MEPP: sistemas lejos del equilibrio maximizan disipación (exploración agresiva) |

### 2.2 Termodinámica de la Información (THD-021 → THD-040)
| ID | Primitiva | Definición Formal |
| :--- | :--- | :--- |
| THD-021 | Información Mutua | I(X;Y) = H(X) − H(X|Y): reducción de incertidumbre compartida |
| THD-022 | Entropía Condicional | H(X|Y): incertidumbre residual después de conocer el estado de Y |
| THD-023 | Divergencia KL | D_KL(P‖Q): costo de usar modelo Q cuando la distribución real es P (slop penalty) |
| THD-024 | Entropía Relativa | Medida asimétrica de distancia entre distribuciones de estado: drift detector |
| THD-025 | Información de Fisher | I(θ) = E[(∂logP/∂θ)²]: sensibilidad de la distribución a cambios de parámetro |
| THD-026 | Capacidad de Canal | C = max I(X;Y): tasa máxima de información sin error por unidad de comunicación |
| THD-027 | Tasa de Distorsión | R(D): mínima tasa de bits para representar fuente con distorsión ≤ D: compresión lossy |
| THD-028 | Entropía de Rényi | H_α(X) = (1/(1−α)) log Σ p_i^α: familia paramétrica de medidas de incertidumbre |
| THD-029 | Entropía de Tsallis | S_q = (1−Σp_i^q)/(q−1): extensión no-extensiva para sistemas con correlaciones de largo alcance |
| THD-030 | Complejidad Termodinámica | W_diss = kT · D_KL(P_forward ‖ P_reverse): trabajo disipado en proceso irreversible |
| THD-031 | Igualdad de Jarzynski | ⟨e^{−W/kT}⟩ = e^{−ΔF/kT}: conexión entre trabajo y energía libre en procesos fuera de equilibrio |
| THD-032 | Teorema de Crooks | P_F(W)/P_R(−W) = e^{(W−ΔF)/kT}: ratio de probabilidades forward/reverse |
| THD-033 | Segunda Ley Generalizada | ⟨W⟩ ≥ ΔF: el trabajo promedio siempre excede el cambio en energía libre |
| THD-034 | Retroalimentación de Maxwell | Reducción de entropía por medición + feedback: information-to-energy conversion |
| THD-035 | Costo de Medición | Adquirir información tiene costo termodinámico: observar el sistema lo perturba |
| THD-036 | Borrado Correlacionado | Borrar bits correlacionados cuesta menos que independientes: compresión termodinámica |
| THD-037 | Información Accesible | Fracción de entropía total que es operacionalmente utilizable por el agente |
| THD-038 | Entropía de Mezcla | ΔS_mix: entropía generada al combinar sistemas previamente separados (merge entropy) |
| THD-039 | Neguentropía | J = S_max − S: entropía disponible para generar orden: capacidad de organización |
| THD-040 | Temperatura de Información | T_info = ∂E/∂S: tasa de cambio de energía con respecto a entropía informacional |

### 2.3 Economía Energética del Cómputo (THD-041 → THD-060)
| ID | Primitiva | Definición Formal |
| :--- | :--- | :--- |
| THD-041 | FLOPS/Watt | Operaciones por segundo por vatio: eficiencia energética del hardware subyacente |
| THD-042 | Tokens/Joule | Tokens generados por julio de energía: eficiencia termodinámica del pipeline LLM |
| THD-043 | Exergía por Token | Fracción de energía por token que produce trabajo útil (acción determinista) vs calor |
| THD-044 | Anergía por Token | Fracción de energía por token que se disipa sin trabajo útil (boilerplate / padding) |
| THD-045 | Costo de Contexto | Energía total para mantener N tokens en la ventana de atención del transformer |
| THD-046 | Presupuesto Térmico | Límite superior de disipación térmica antes de throttling o degradación del sistema |
| THD-047 | Eficiencia de Carnot del Pipeline | η_pipeline = (Exergía_output) / (Exergía_input): fracción útil de la computación |
| THD-048 | Costo de Atención | O(n²) energía para self-attention: escala cuadrática con longitud de contexto |
| THD-049 | Presupuesto Exergético Total | Suma de exergías asignables a todas las operaciones de un ciclo completo |
| THD-050 | Waste Heat Computacional | Calor generado por operaciones que no contribuyen al resultado (retries, hallucinations) |
| THD-051 | Amortización Energética | Distribución del costo de entrenamiento del modelo sobre sus N inferencias |
| THD-052 | ROI Termodinámico | Retorno de inversión medido en bits útiles por julio invertido |
| THD-053 | Densidad de Exergía | Exergía por unidad de volumen de estado (bits útiles por byte de almacenamiento) |
| THD-054 | Cascada Exergética | Transferencia de exergía entre etapas del pipeline: cada etapa recibe la exergía residual |
| THD-055 | Reciclaje de Exergía | Reutilización de resultados intermedios para evitar recomputación (caching termodinámico) |
| THD-056 | Pérdida por Serialización | Energía gastada en convertir estado interno a formato transmisible (JSON, protobuf) |
| THD-057 | Costo de Sincronización | Energía para garantizar consistencia entre N réplicas del estado (consensus overhead) |
| THD-058 | Energía de Activación | Barrera mínima de energía para iniciar una transición de estado (bootstrap cost) |
| THD-059 | Punto de Curie Computacional | Temperatura crítica donde el sistema pierde coherencia magnética / organizacional |
| THD-060 | Degradación Entrópica | Tasa de pérdida de exergía por unidad de tiempo sin intervención (context rot rate) |

### 2.4 Mecánica Estadística del Cómputo (THD-061 → THD-080)
| ID | Primitiva | Definición Formal |
| :--- | :--- | :--- |
| THD-061 | Distribución de Boltzmann | P(s) ∝ e^{−E(s)/kT}: probabilidad de un microestado dado su nivel energético |
| THD-062 | Función de Partición | Z = Σ e^{−E_i/kT}: normalizadora que codifica toda la termodinámica del sistema |
| THD-063 | Ensemble Canónico | Colección de estados a temperatura constante: distribución de configuraciones del swarm |
| THD-064 | Ensemble Microcanónico | Colección de estados a energía constante: exploración ergódica de configuraciones |
| THD-065 | Ensemble Gran Canónico | Estados con intercambio de partículas/agentes: swarm con tamaño variable |
| THD-066 | Ergodicidad | Promedio temporal = promedio de ensemble: el agente explora todos los estados accesibles |
| THD-067 | Ruptura de Ergodicidad | Sistema atrapado en subconjunto de estados: dead-end / local minimum del pipeline |
| THD-068 | Transición de Fase | Cambio discontinuo de comportamiento al variar un parámetro: colapso/emergencia abrupta |
| THD-069 | Parámetro de Orden | Observable que distingue fases: métrica de coherencia del sistema (C1→C5) |
| THD-070 | Punto Crítico | Divergencia de correlaciones: punto donde el sistema es maximalmente sensible |
| THD-071 | Exponente Crítico | Leyes de potencia cerca de transiciones: escalado de comportamiento emergente |
| THD-072 | Grupo de Renormalización | Transformación que cambia escala preservando física: coarse-graining del estado |
| THD-073 | Universalidad | Clases de sistemas con mismos exponentes críticos: isomorfismo termodinámico entre dominios |
| THD-074 | Simetría Rota | Estado fundamental con menos simetría que el hamiltoniano: especialización espontánea |
| THD-075 | Modo de Goldstone | Excitación sin masa que emerge de simetría rota: grado de libertad residual |
| THD-076 | Nucleación | Formación de nueva fase dentro de la vieja: bootstrap de nuevo subsistema |
| THD-077 | Spinodal | Límite de metaestabilidad: punto donde el sistema DEBE transicionar (deadline) |
| THD-078 | Histéresis | Dependencia del estado actual en la historia: memoria termodinámica del sistema |
| THD-079 | Vidrio de Espín | Estado desordenado congelado: sistema con frustración máxima (deadlock multiagente) |
| THD-080 | Temple Simulado | Optimización por enfriamiento gradual: reducción controlada de exploración estocástica |

### 2.5 Termodinámica de Sistemas Abiertos (THD-081 → THD-100)
| ID | Primitiva | Definición Formal |
| :--- | :--- | :--- |
| THD-081 | Estructura Disipativa | Orden que emerge y se mantiene por flujo constante de energía (sistema vivo) |
| THD-082 | Autopoiesis Termodinámica | Sistema que se reproduce y mantiene a sí mismo usando flujos disipativos |
| THD-083 | Frontera del Sistema | Membrana que define qué es interior (agente) y exterior (entorno): process boundary |
| THD-084 | Flujo de Entropía | dS/dt = dS_i/dt + dS_e/dt: producción interna + intercambio con exterior |
| THD-085 | Acoplamiento Termodinámico | Uso de un proceso espontáneo para impulsar uno no-espontáneo: subsidio cruzado |
| THD-086 | Principio de Le Chatelier | Sistema en equilibrio responde a perturbación minimizándola: resistencia a cambio |
| THD-087 | Régimen Lineal | Cerca del equilibrio: flujos proporcionales a fuerzas: comportamiento predecible |
| THD-088 | Régimen No-Lineal | Lejos del equilibrio: bifurcaciones, oscilaciones, caos: comportamiento emergente |
| THD-089 | Reciprocidad de Onsager | L_ij = L_ji: simetría de coeficientes de transporte cruzado: fairness de intercambio |
| THD-090 | Efecto Peltier Computacional | Flujo de información que genera o absorbe entropía en la frontera |
| THD-091 | Efecto Seebeck Computacional | Gradiente de entropía que genera flujo de información: información emergente de ruido |
| THD-092 | Ciclo de Carnot Computacional | Ciclo ideal: input→compress→compute→expand→output con eficiencia máxima |
| THD-093 | Ciclo Otto Computacional | Ciclo real con compresión/expansión isocórica: batch processing con overhead |
| THD-094 | Bomba de Calor Informacional | Transferencia de entropía de sistema frío (organizado) a caliente (caótico): garbage collection |
| THD-095 | Refrigeración Algorítmica | Reducción de entropía de qubits/bits de interés a costa de bits auxiliares |
| THD-096 | Entropía de Clausius | dS = δQ_rev/T: definición original conectando calor y entropía |
| THD-097 | Exergía de Flujo | Exergía transportada por flujo de materia/información a través de frontera del sistema |
| THD-098 | Destrucción de Exergía | Exergía irrecuperablemente perdida por irreversibilidades internas (bugs, retries) |
| THD-099 | Balance Exergético | Σ(Ex_in) = Σ(Ex_out) + Σ(Ex_destroyed): contabilidad completa de recursos |
| THD-100 | Apoptosis Termodinámica | Muerte programada de un proceso cuando su balance exergético es negativo neto |