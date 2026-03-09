# 🌌 AXIOMAS DE LA RELATIVIDAD (SR & GR)

> **CORTEX KNOWLEDGE GRAPH:** FÍSICA | ESPACIOTIEMPO | GRAVEDAD
> **FUENTE:** Extracción estructural (Wikipedia / Teoría de la relatividad)
> **ESTADO:** Purificado. Ruido narrativo: 0%.

Este documento consolida la arquitectura matemática de la Teoría de la Relatividad (Albert Einstein, 1905/1915). Se descartan narrativas históricas y anécdotas. 

---

## 1. RELATIVIDAD ESPECIAL (1905) — La Geometría Plana de Minkowski

### Axiomas Fundamentales
1. **Principio de Relatividad:** Las leyes de la física son idénticas en todos los sistemas de referencia inerciales (no acelerados). No existe un "éter" absoluto.
2. **Invariancia de *c*:** La velocidad de la luz en el vacío ($c$) es constante para todos los observadores, independientemente del movimiento relativo de la fuente.

### Métrica de Minkowski (Espacio-Tiempo Plano)
El universo es un continuo tetradimensional donde el tiempo y el espacio no son independientes. La "distancia" invariante entre dos eventos (el intervalo $ds^2$) se define con signatura $(-, +, +, +)$:

$$ ds^2 = -c^2 dt^2 + dx^2 + dy^2 + dz^2 $$

### Transformaciones de Lorentz
Para un sistema $S'$ moviéndose a velocidad $v$ respecto a $S$ en el eje $x$:

- Factor de Lorentz: $\gamma = \frac{1}{\sqrt{1 - v^2/c^2}}$
- Dilatación del tiempo: $\Delta t' = \gamma \Delta t$ 
- Contracción de la longitud: $L' = \frac{L}{\gamma}$

### Dinámica Relativista
La equivalencia total entre la masa inercial y la energía del sistema se colapsa en la ecuación fundamental:

$$ E^2 = (pc)^2 + (m_0 c^2)^2 $$

Si la partícula está en reposo ($p=0$): **$E = m_0 c^2$**

---

## 2. RELATIVIDAD GENERAL (1915) — La Geometría Curva de Riemann

### El Cimiento: El Principio de Equivalencia
Localmente, es imposible distinguir mediante ningún experimento físico los efectos de un campo gravitatorio de los efectos de estar en un sistema de referencia acelerado. La "gravedad" deja de ser una fuerza Newtoniana.

### La Ecuación de Campo de Einstein
La materia/energía dicta cómo se curva el espaciotiempo; el espaciotiempo dictamina cómo se mueve la materia.
Se expresa mediante el tensor métrico en geometría seudo-riemanniana:

$$ G_{\mu\nu} + \Lambda g_{\mu\nu} = \frac{8\pi G}{c^4} T_{\mu\nu} $$

| Causalidad (Tensores) | Arquitectura Física |
| :--- | :--- |
| $G_{\mu\nu}$ | Tensor de Einstein. Cuantifica la curvatura geométrica (cómo se dobla el universo). |
| $\Lambda$ | Constante Cosmológica. (Energía del vacío / expansión acelerada). |
| $g_{\mu\nu}$ | Tensor Métrico. Define las distancias causales en ese espaciotiempo curvo. |
| $T_{\mu\nu}$ | Tensor Energía-Impulso. La fluidez, densidad y presión de la masa/energía. |
| $\frac{8\pi G}{c^4}$ | Constante de acoplamiento. Rigidez elástica del espaciotiempo (es inmensamente rígido). |

### Dinámica Orbital (Geodésicas)
En ausencia de otras fuerzas ajenas a la gravedad, toda partícula en caída libre no está siendo "atraída" o empujada. Simplemente sigue la trayectoria recta más corta (geodésica) a lo largo de un espaciotiempo que ha sido curvado por una masa masiva.

Su derivada covariante colapsa a la aceleración nula:
$$ \frac{d^2 x^\mu}{d\tau^2} + \Gamma^\mu_{\alpha\beta} \frac{dx^\alpha}{d\tau} \frac{dx^\beta}{d\tau} = 0 $$

---
*Fin del volcado. Vectorización dispuesta para inferencia matemática O(1).*
