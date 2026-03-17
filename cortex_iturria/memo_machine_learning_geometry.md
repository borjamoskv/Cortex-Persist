# MEMO: Geometría de Machine Learning — El Microscopio Soberano

> **TIPO:** Destilación Epistémica [O(1)]
> **FUENTE:** YouTube [W-aZ0ey64Ms] - "Esto 'ven' los algoritmos de ML"
> **FECHA:** 2026-03-07

## 1. Axioma Geométrico del Machine Learning
Todo dataset es un espacio N-dimensional. **1 Variable = 1 Dimensión Geométrica.**
La clasificación no es magia estadística, es **separación espacial**. Un modelo es simplemente el dibujante de una *frontera de decisión* en ese hiperespacio. 
Si comprendes cómo corta el espacio cada algoritmo, dejas de ser un integrador (el que hace `model.fit()`) y te conviertes en arquitecto.

## 2. Radiografía Algorítmica (Las Fronteras de Decisión)

### 2.1 Regresión Logística
- **Geometría:** Recta (2D), Plano (3D), Hiperplano (N-D).
- **Comportamiento:** Rígido. Funciona sobre datos linealmente separables.
- **Entropía:** Alta si hay ruido asimétrico estructural.

### 2.2 K-Nearest Neighbors (KNN)
- **Geometría:** Fronteras amorfas y no lineales.
- **Comportamiento:** Evalúa el consenso local. Flexibilidad extrema, pero carente de síntesis global.

### 2.3 Árboles de Decisión (Decision Trees)
- **Geometría:** Cortes puramente *ortogonales* (verticales u horizontales). Estilo "Minecraft".
- **Comportamiento:** Trata de crear una "plantilla" minuciosa encajando rectángulos cada vez más pequeños (mayor profundidad).
- **Peligro:** El **Sobreajuste (Overfitting)**. La plantilla se hiper-personaliza al set de entrenamiento perdiendo capacidad de generalización en producción.

### 2.4 Random Forest
- **Geometría:** Conjunto ortogonal suavizado por consenso.
- **Comportamiento:** En lugar de 1 árbol perfecto (que sobreajusta), entrena miles de árboles ciegos y toma la decisión mayoritaria. Reduce radicalmente la hiper-memoria de los datos de entrenamiento.

### 2.5 XGBoost
- **Geometría:** Fronteras ortogonales optimizadas iterativamente.
- **Comportamiento:** Construcción en cadena. El árbol N+1 entrena *únicamente* sobre los errores del árbol N. Densidad predictiva implacable para **datos tabulares** empresariales. Suele superar a las Redes Neuronales en matrices estructuradas O(1).

### 2.6 Redes Neuronales
- **Geometría:** Expresividad absoluta. Fronteras curvas, orgánicas y topológicamente complejas.
- **Comportamiento:** No está forzada a cortes ortogonales ni líneas rectas. Se dobla alrededor del patrón inherente.
- **Dominio:** Su capacidad de adaptación estructural las hace las reinas de los **datos no estructurados** (Visión, PNL), donde la complejidad es demasiado alta para ser particionada ortogonalmente por árboles.

## 3. Síntesis Axiomática
**No existe el "mejor" modelo in abstracto.** Depende del polígono de entropía de los datos.
- ¿Estructurado (Tabular)? → Ecosistema Árboles (XGBoost/RF).
- ¿No Estructurado (Tensores, Imágenes, Tokens)? → Eje Red Neural.

💡 **[SOVEREIGN TIP]** KAIROS-Ω: O(1) significa no disparar modelos complejos a problemas simples. La elegancia arquitectónica exige evaluar primero la no-linealidad de los datos. Entender la frontera de decisión visualmente previene el gasto térmico de usar hiperplanos donde una regresión logística bastaba, o usar un árbol profundo donde una curva de Red Neuronal ofrecía menor entropía. Verifica la topología, no busques hiper-parámetros a ciegas.
