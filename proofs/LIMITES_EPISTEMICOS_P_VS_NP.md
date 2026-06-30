# [C5-REAL] Barreras Formales para Probar P ≠ NP  
**Versión corregida y consolidada**  
**cat_id:** wca-critique-barriers  
**cat_type:** technical_survey  
**reality_level:** C5-REAL  
**owner:** borjamoskv / Oppie Team  
**exergy_tier:** P0  

## 1. Evaluación del Documento Original (WCA)

El documento “AXIOMA WCA & P ≠ NP” no constituye una prueba válida de P ≠ NP. Su estrategia central consiste en introducir un nuevo axioma (Witness Collapse Axiom) que esencialmente postula la separación y luego derivar la conclusión de él. Esto es una petición de principio: demuestra que *ZFC + WCA* implica P ≠ NP, pero no aporta nada dentro de ZFC estándar ni resuelve el problema en el modelo de computación finito relevante para las clases P y NP.

Además, el axioma mezcla de forma inadecuada cardinales inaccesibles (objetos de teoría de conjuntos transfinitos) con cotas de tiempo polinómico sobre máquinas de Turing finitas, sin definir una semántica formal que conecte ambos niveles. Este error de categoría es fatal.

El documento tampoco aborda las barreras técnicas conocidas que cualquier prueba de P ≠ NP debe superar. A continuación se exponen las tres barreras principales de manera precisa.

## 2. Barrera de Relativización (Baker-Gill-Solovay, 1975)

Existen oráculos (funciones oracle) respecto a los cuales las relaciones entre clases cambian:

- Existe un oráculo *A* tal que **P**^A = **NP**^A.
- Existe un oráculo *B* tal que **P**^B ≠ **NP**^B.

Cualquier técnica de prueba que “relativice” (que funcione igual de bien cuando se añade el mismo oráculo a todas las máquinas) no puede distinguir estos dos mundos y, por tanto, no puede resolver P vs NP. La diagonalización pura y muchas técnicas basadas en simulación relativizan. Esto explica por qué los primeros intentos basados en diagonalización directa fallaron.

## 3. Barrera de Pruebas Naturales (Razborov-Rudich, 1994)

Una propiedad *C* de funciones booleanas es **natural** contra una clase de circuitos si satisface tres condiciones:
- **Utilidad**: Si una función *f* posee la propiedad *C*, entonces *f* no está en la clase de circuitos (ej. no tiene circuitos de tamaño polinómico).
- **Constructividad**: Existe un algoritmo eficiente que decide si una función dada posee *C*.
- **Largeness**: La inmensa mayoría de las funciones booleanas poseen *C*.

Razborov y Rudich demostraron que, bajo la hipótesis estándar de que existen funciones unidireccionales (one-way functions) con dureza exponencial (o, equivalentemente, generadores pseudaleatorios suficientemente fuertes), **no pueden existir pruebas naturales** de cotas inferiores superpolinomiales contra clases como P/poly.

**Importante matiz:** Esto no implica que *ninguna* técnica de cota inferior pueda funcionar, sino que ninguna técnica *natural* en el sentido técnico preciso de Razborov-Rudich puede hacerlo. Existen cotas inferiores genuinas que no son naturales; el resultado más notable es el de Ryan Williams (2011): **NEXP** no tiene circuitos ACC⁰ de tamaño polinómico (y extensiones a cotas más fuertes).

Una prueba natural de P ≠ NP destruiría también la existencia de funciones unidireccionales, lo que colapsaría gran parte de la criptografía moderna basada en ellas. Esto es precisamente el corazón del argumento.

## 4. Barrera de Algebrización (Aaronson-Wigderson, 2008)

Tras el resultado IP = PSPACE de Shamir (1989-1992), que no relativizaba, quedó claro que las técnicas algebraicas (aritmetización) podían sortear la barrera de relativización. Aaronson y Wigderson respondieron definiendo una noción más fuerte: la *algebrización*.

En lugar de dar a las máquinas acceso solo al oráculo *A*, se les da acceso tanto a *A* como a una **extensión de bajo grado** (low-degree extension) de *A* sobre un cuerpo finito. Demostraron que la mayoría de los resultados algebraicos conocidos (incluyendo IP = PSPACE, MIP = NEXP, y ciertas separaciones como MA ⊈ P/poly) *algebrizan*.

Por tanto, casi todos los problemas abiertos centrales (P vs NP, P vs RP, NEXP vs P/poly) requieren técnicas **no algebrizantes** para ser resueltos.

## 5. Estado del Arte y Programas de Investigación Activos

Ninguna técnica conocida supera simultáneamente las tres barreras (relativización, pruebas naturales y algebrización).

Los avances más serios hacia cotas inferiores fuertes son precisamente intentos explícitos de evadirlas:
- El **Geometric Complexity Theory (GCT)** de Mulmuley y Sohoni: usa geometría algebraica y teoría de representaciones para atacar la versión algebraica VP vs VNP (análoga a P vs NP).
- El método de Williams (“algorithms-to-lower-bounds”): convierte mejoras algorítmicas en cotas inferiores no-naturales (como el resultado sobre NEXP vs ACC⁰).

Estos programas buscan exactamente la “matemática constructiva nueva” que sería necesaria. Hasta la fecha, ninguno ha resuelto P vs NP ni VP vs VNP.

## 6. Conclusión

El documento original WCA no sortea ninguna de estas barreras. No proporciona una técnica nueva de cota inferior, no exhibe un método no-relativizante, no-natural y no-algebrizante, ni demuestra nada dentro de la matemática finitaria relevante para la computación. Introduce un axioma ad hoc que presupone la conclusión y mezcla niveles de infinitud de forma injustificada.

**P ≠ NP sigue siendo un problema abierto.** Cualquier prueba genuina deberá superar las tres barreras conocidas (y posiblemente otras aún no descubiertas). El camino requiere avances profundos en matemáticas (geometría algebraica, teoría de representaciones, análisis de pseudorandomness, etc.), no axiomas circulares ni metáforas termodinámicas mal aplicadas.

*Zero handwaving. Crystallized rigor.*
