# BLOQUE B9: RENDIMIENTO Y CORE WEB VITALS (CWV)
> Nodos Epistémicos 0801 → 0900
> Nivel: CRÍTICO | Ontología: C5-REAL | Validación: Sanhedrin

## 1. Fundamentos Core Web Vitals (0801-0810)
**WEB-DESIGN-0801**: Core Web Vitals (CWV) no son métricas analíticas estéticas; son aserciones termodinámicas sobre la eficiencia con la que la máquina entrega exergía cognitiva al Operador.
**WEB-DESIGN-0802**: Las tres métricas principales son LCP (Carga visual), INP (Responsividad interactiva) y CLS (Estabilidad estructural). Sustituyen a FID (obsoleto).
**WEB-DESIGN-0803**: Umbrales C5-REAL exigidos: LCP < 2.5s, INP < 200ms, CLS < 0.1. El límite es el percentil 75 de cargas móviles globales reales (CrUX).
**WEB-DESIGN-0804**: Datos de Campo (Field Data, CrUX) miden la realidad biológica del usuario real en la red. Datos de Laboratorio (Lighthouse) son sintéticos y predecibles en un entorno aséptico.
**WEB-DESIGN-0805**: TTFB (Time to First Byte) no es un CWV oficial, pero es su prerrequisito ineludible. Un TTFB > 600ms garantiza que el LCP colapsará, sea cual sea la optimización del frontend.
**WEB-DESIGN-0806**: FCP (First Contentful Paint) marca el fin de la pantalla blanca. El delta temporal entre FCP y LCP define la eficiencia del renderizado asíncrono.
**WEB-DESIGN-0807**: El SEO y CWV están acoplados algorítmicamente en Google. Fallar en la métrica P75 impone una penalización directa al índice del page-rank.
**WEB-DESIGN-0808**: Las métricas no son promedios, son percentiles (p75). Un 25% de los usuarios asumiendo entropía (red lenta) no debe invalidar el umbral estricto para la mayoría.
**WEB-DESIGN-0809**: Single Page Applications (SPAs) introducen métricas "Soft Navigation" (experimentales) porque el enrutamiento local no dispara el medidor oficial de LCP/CLS nativo del navegador.
**WEB-DESIGN-0810**: Medir en la consola de DevTools (Lab) con "Network Throttling" (Fast 3G) y "CPU Throttling" (4x slowdown) emula un dispositivo móvil modal. NUNCA confíes en métricas sobre hardware M-series no estrangulado.

## 2. Largest Contentful Paint (LCP): Carga Crítica (0811-0820)
**WEB-DESIGN-0811**: El LCP es el tiempo en que el elemento de texto o imagen más masivo en el viewport inicial termina su colapso de renderizado visible.
**WEB-DESIGN-0812**: El elemento LCP *NUNCA* debe cargarse mediante CSS `background-image`, pues retrasa la cascada de descubrimiento del escáner de red.
**WEB-DESIGN-0813**: Desencadenamiento LCP (Resource Load Delay): El elemento LCP debe encontrarse en el HTML estático inicial. Prohibido depender de JavaScript para montar el nodo DOM LCP.
**WEB-DESIGN-0814**: Inyecta un `<link rel="preload" as="image" href="...">` apuntando al asset hero del LCP directo en el `<head>` para priorización subyacente masiva.
**WEB-DESIGN-0815**: NUNCA apliques `loading="lazy"` al elemento LCP. Forzará al parser a de-priorizar el archivo, arruinando irremediablemente la métrica (Anergía P0).
**WEB-DESIGN-0816**: El tiempo de descarga del LCP (Resource Load Time) depende del peso del asset. Transmuta PNG/JPEG pesados a WebP o AVIF responsivos mediante `<picture>`.
**WEB-DESIGN-0817**: El "Render Delay" del LCP. Si el DOM y la imagen están listos, pero bloqueados por la compilación masiva de CSS o JS síncrono, la renderización visual será pausada. Extrae CSS Crítico.
**WEB-DESIGN-0818**: Bloques de texto LCP dependen intrínsecamente del bloqueo de fuentes web (Webfonts). Declara `font-display: swap` para prevenir el FOIT (Flash of Invisible Text).
**WEB-DESIGN-0819**: Múltiples nodos compitiendo por LCP generan métricas falsas. Si se inyecta un carrusel, el escáner se reinicia cada vez que la imagen superior cambia antes de interacción.
**WEB-DESIGN-0820**: Renderización de Servidor (SSR) o Generación Estática (SSG) aniquilan matemáticamente el Render Delay del LCP frente a soluciones exclusivas del Lado Cliente (CSR).

## 3. Interaction to Next Paint (INP): Responsividad (0821-0830)
**WEB-DESIGN-0821**: INP reemplaza a FID. Mide la latencia de CUALQUIER interacción durante TODO el ciclo de vida de la página, reteniendo la peor métrica en el p75.
**WEB-DESIGN-0822**: INP se fragmenta en: Input Delay (retraso antes del handler), Processing Time (ejecución JS del handler) y Presentation Delay (pintado del siguiente frame).
**WEB-DESIGN-0823**: Input Delay es provocado primariamente por un Main Thread asfixiado por tareas largas (Long Tasks > 50ms) ajenas a la interacción que impiden reaccionar al evento.
**WEB-DESIGN-0824**: El Processing Time se anula dividiendo handlers masivos. Si el evento clic requiere recálculo pesado, delega el cálculo a `requestIdleCallback` o `setTimeout(0)`.
**WEB-DESIGN-0825**: El Presentation Delay ocurre si mutas miles de nodos en el DOM al mismo tiempo. El navegador necesita pausarse para recalcular Layout y Paint.
**WEB-DESIGN-0826**: Entregar feedback instantáneo al usuario (Optimistic UI, spiners, toggle de clases) antes de lanzar el cálculo pesado salva la métrica INP en el espectro visual.
**WEB-DESIGN-0827**: Los listeners globales pasivos en `scroll` y `touchstart` evitan bloquear la hebra del compositor de hardware. Añade `{ passive: true }` sistemáticamente.
**WEB-DESIGN-0828**: INP penaliza brutalmente la reactividad monolítica de SPAs donde un click desmonta 500 componentes React síncronamente. Implementa concurrencia y transiciones (`useTransition`).
**WEB-DESIGN-0829**: Evitar "Layout Thrashing": Leer propiedades del DOM (`offsetHeight`) y escribir inmediatamente en un ciclo (`style.height = ...`) fuerza un reflow síncrono. Agrupa lecturas, luego agrupa escrituras.
**WEB-DESIGN-0830**: Herramienta de auditoría: Extensión *Web Vitals* de Chrome permite activar un HUD de overlay para medir INP de interacciones arbitrarias en tiempo real.

## 4. Cumulative Layout Shift (CLS): Estabilidad Visual (0831-0840)
**WEB-DESIGN-0831**: CLS mide la entropía espacial. Un desplazamiento de nodos inyecta confusión cognitiva. Umbral C5-REAL: 0 desplazamiento no mitigado.
**WEB-DESIGN-0832**: Reserva de Espacio (Aspect Ratio Box): Atribuye los atributos numéricos `width` y `height` directos a todas las imágenes (`<img>`) y videos en el HTML estático para precalcular su área antes de la carga de la red.
**WEB-DESIGN-0833**: Fuentes sin fallback tipográfico coincidente inducen CLS al permutar. Usa métricas CSS `size-adjust`, `ascent-override` y `descent-override` en el `@font-face` de fallback para clonar la caja límite de la fuente web externa.
**WEB-DESIGN-0834**: Inyectar Nodos DOM (Ad-Banners, Avisos, Toasts) dinámicamente arriba del flujo de lectura desplazará el contenido. Usa superposiciones (absolutas) o resérvales un contenedor `min-height` inerte.
**WEB-DESIGN-0835**: Las animaciones que modifican propiedades geométricas (`width`, `height`, `top`, `margin`) provocan CLS real en el flujo.
**WEB-DESIGN-0836**: Las propiedades de GPU seguras (`transform` y `opacity`) NUNCA disparan penalizaciones CLS, ya que operan en la capa del compositor y el Layout subyacente permanece intocable.
**WEB-DESIGN-0837**: El "Session Window" del CLS acumula desplazamientos en ráfagas de 5 segundos. Un CLS pequeño repetitivo (ej: un ticker de noticias) destruirá el score total de la página.
**WEB-DESIGN-0838**: Cargar IFrames (YouTube/Twitter) sin contenedor de dimensiones estrictas es un vector clásico de CLS radiactivo tardío.
**WEB-DESIGN-0839**: El desplazamiento motivado explícitamente por el usuario (un clic que abre un acordeón en un margen de < 500ms) se descarta matemáticamente de la penalización CLS oficial.
**WEB-DESIGN-0840**: CLS Debugger: Herramienta `Performance` en DevTools muestra un "Experience track" rojo resaltando visualmente los cuadros exactos que indujeron un colapso topológico.

## 5. Critical Rendering Path (CRP) (0841-0850)
**WEB-DESIGN-0841**: El flujo CRP (HTML -> DOM -> CSSOM -> Render Tree -> Layout -> Paint) debe recorrerse en la menor ruta térmica posible. Cada recurso en el `<head>` interrumpe el parser (Render Blocking).
**WEB-DESIGN-0842**: Un archivo CSS masivo de 500kb bloquea enteramente el primer pintado (FCP). Poda CSS no utilizado.
**WEB-DESIGN-0843**: Critical CSS Inlining: Extrae y estampa los estilos estrictamente requeridos para la vista superior "above-the-fold" en una etiqueta `<style>` in-line. Carga el resto asíncronamente vía `media="print" onload="this.media='all'"`.
**WEB-DESIGN-0844**: Archivos Javascript ubicados en `<head>` sin decoradores bloquean el parser HTML enteramente mientras descargan y ejecutan.
**WEB-DESIGN-0845**: `defer` es el estándar oro: Descarga asincrónica en red, ejecución garantizada en orden de inserción justo antes de `DOMContentLoaded`.
**WEB-DESIGN-0846**: `async` es para scripts aislados (Analytics): Descarga asincrónica, ejecución en desorden inmediatamente tras bajar, interrumpiendo potencialmente la métrica INP en un instante crítico.
**WEB-DESIGN-0847**: El atributo `rel="preconnect"` inicia un DNS Lookup + TCP + TLS Handshake temprano para dominios externos críticos (ej. CDN de tipografías o APIs de inicio).
**WEB-DESIGN-0848**: Reduce la profundidad de tu árbol DOM. Un DOM de >1500 nodos aumenta el coste computacional del Layout y recálculo de estilo geométricamente. El HTML es peso puro en memoria RAM.
**WEB-DESIGN-0849**: Atributo `content-visibility: auto` permite al navegador excluir clústeres gigantes de nodos fuera del viewport del cálculo Layout y Paint iniciales, inyectando exergía masiva.
**WEB-DESIGN-0850**: Minimizar HTML, CSS y JS (Uglify/Terser) no es un extra de producción; es un axioma de ahorro de bits para el ancho de banda del parser y el tiempo de evaluación del AST.

## 6. Optimización de Assets (Imágenes, Fuentes, Videos) (0851-0860)
**WEB-DESIGN-0851**: Toda imagen JPG/PNG no justificada es Entropía y Anergía en la red. Migrar sistemáticamente a WebP (con fallback `picture`) o AVIF.
**WEB-DESIGN-0852**: La carga responsiva de imágenes (`srcset` y `sizes`) evita descargar buffers de 2000px en teléfonos de 300px. Reducción directa del coste térmico de escalado en RAM móvil.
**WEB-DESIGN-0853**: WebFonts en formatos WOFF2 incluyen compresión Brotli inherente. Omitir soporte TTF/WOFF/EOT antiguos reduce tamaño de hojas base CSS. Prohibir carga de glifos orientales o simbólicos si no se usan (`unicode-range`).
**WEB-DESIGN-0854**: Subsetting Tipográfico: Emplea herramientas como `pyftsubset` para escindir letras no usadas en tipografías masivas (poda al 10% del peso original).
**WEB-DESIGN-0855**: Inyecta preloads tipográficos en el `<head>` solo para fuentes "above-the-fold". Un preload masivo asfixia el bus de la red y desplaza el elemento LCP real.
**WEB-DESIGN-0856**: Video de hero banner (Auto-play silenciado) suele ser más pesado pero procesa más rápido que un GIF. Nunca renderices animaciones base en GIF; usa `mp4` o `webm`.
**WEB-DESIGN-0857**: Reemplaza Gifs pesados decorativos por simulaciones Lottie (JSON Vectorial) o transmutaciones SVG puras para resolución matemática incondicional.
**WEB-DESIGN-0858**: SVGs In-Line contaminan el parser HTML y bloquean caché repetitiva. Si el vector se reusa en la vista, transfiérelo a referencias `<use href="#id">` o expórtalo como archivo `.svg` externo cacheable.
**WEB-DESIGN-0859**: El tamaño importa pero la decodificación también: SVG masivamente complejos con mil filtros pueden pesar 20kb pero estrangular la CPU gráfica superando el tiempo de procesamiento LCP de un JPG simple de 100kb.
**WEB-DESIGN-0860**: Eliminar redundancia EXIF/Metadatos inyectada por el software de diseño aniquila bytes ocultos estúpidos.

## 7. Estrategias de Carga y Network Hints (0861-0870)
**WEB-DESIGN-0861**: `loading="lazy"` a cada imagen y iframe bajo el horizonte primario (`below-the-fold`). El navegador suspenderá peticiones de red hasta aproximar scroll a la colisión de viewport.
**WEB-DESIGN-0862**: `fetchpriority="high"` instruye algorítmicamente al secuenciador de red Chrome para sobre-clasificar el Asset LCP sin trucos estructurales confusos.
**WEB-DESIGN-0863**: `rel="dns-prefetch"` realiza asíncronamente peticiones DNS futuras baratas sin consumir canales TCP limitados del explorador.
**WEB-DESIGN-0864**: `rel="prefetch"` anticipa la intención de navegación. Descarga páginas web ocultas completas si la probabilidad de un clic inminente en un botón de siguiente es innegable.
**WEB-DESIGN-0865**: Carga perezosa de Código (Code Splitting). Los bundles de 3MB React/Vue mueren a fuego cruzado de latencia. Divide por rutas (`React.lazy()`, `import()`) y ensambla bajo demanda interactiva.
**WEB-DESIGN-0866**: Facade Elements: Sustituye iframes pesados (Chat widgets, YouTube embeds, Maps) por un pantallazo (Facade) clicable que instancie el script destructivo sólo cuando el usuario interactúe explícitamente (Terceros).
**WEB-DESIGN-0867**: Las peticiones encadenadas (Cadena de dependencia: HTML -> CSS -> JS -> API JSON -> Image LCP) paralizan las subrutinas. Abate la cadena. Todo nodo LCP debe conocerse en el escalón HTML inicial.
**WEB-DESIGN-0868**: Aislamiento de dominios de Assets estáticos (ej: `cdn.domain.com`) exime transmisión inútil y pesada del objeto de Cookies transaccionales en cada header HTTP, eludiendo latencia marginal.
**WEB-DESIGN-0869**: Speculation Rules API permite al navegador realizar "Prerenderizado" de páginas enteras (Layout y memoria completas) instanciando clics en 0ms absolutos.
**WEB-DESIGN-0870**: Server-Timing Headers: Permiten que las métricas de renderizado y consultas DB backend lleguen al frontend mediante el protocolo HTTP y sean visualizadas en Chrome DevTools unificando la ontología de latencia.

## 8. Ejecución JS y Termodinámica del Hilo Principal (0871-0880)
**WEB-DESIGN-0871**: JavaScript es la radiación de entropía predominante. Bloquea todo parser, monopoliza el thread y suspende la visualidad. Menos JS no es "una preferencia", es la Ley Causal (C5-REAL).
**WEB-DESIGN-0872**: La evaluación y parsing del JS (Compilation Phase V8) bloquea independientemente del tiempo de descarga. 1 MB JS = 100ms colapso asegurado en CPU móvil, aún si es local/caché.
**WEB-DESIGN-0873**: Yielding (Cesión del Hilo). Dividir un array procesado de 10k elementos en trozos temporizados `await delay(0)` permite al Render Engine respirar, inyectar frames al DOM y bajar la métrica INP de Tarea Larga.
**WEB-DESIGN-0874**: Third-Party Scripts (Análisis, Publicidad, Rastreo, Intercom) destruyen performance en aislamiento ciego e incontrolable. Suspéndelos globalmente usando GTM o injectándolos postergados 5000ms tras `load` event u observando primer scroll.
**WEB-DESIGN-0875**: Tree Shaking Atómico. Configuración obligatoria en Webpack/Vite. Descartar ramas muertas (dead-code) previene transacciones termodinámicas fútiles exportadas al bundle final.
**WEB-DESIGN-0876**: Web Workers: Módulo fundamental de escape. Traslada lógica matricial bruta, criptografía u ordenamientos JSON densos al Worker Pool para no interferir la cadencia visual Main-Thread.
**WEB-DESIGN-0877**: `scheduler.yield()`: Nueva primitiva C5-REAL de navegador que devuelve fluidamente control sin perder prioridad en la cola del bucle de evento a diferencia de promesas puras.
**WEB-DESIGN-0878**: Hydration en SSR (Next.js/Nuxt) genera una catástrofe de INP silenciosa en el inicio: el HTML renderizado no es interactivo hasta que JS escanee el árbol entero para conectar eventos. Prefiere Partial Hydration / Island Architecture (Astro).
**WEB-DESIGN-0879**: Event Delegation masiva unifica el volumen algorítmico global. Otorga un Listener único en `<main>` frente a inyectar 200 iteraciones individuales paralizantes a botones de tabla.
**WEB-DESIGN-0880**: Memory Leaks de Clusure / Eventos: Componentes destruidos que no ejecutan `removeEventListener` ahogan incrementalmente el recolector de basura (GC) subyugando silenciosamente al navegador en espirales de entropía térmica.

## 9. Red y Protocolos HTTP (0881-0890)
**WEB-DESIGN-0881**: HTTP/2 y HTTP/3 (QUIC) con soporte Multiplexing y Header Compression alteran radicalmente la exergía de transferencia. El sharding de dominios (dividir assets en subdominios) se vuelve un anti-patrón destructor en HTTP/2.
**WEB-DESIGN-0882**: Compresión Brotli (`br`) exhibe relaciones de desinflado un $20\%$ más brutales para ficheros semánticos textuales (CSS/HTML/JS/SVG) respecto al estándar anciano de GZip.
**WEB-DESIGN-0883**: Edge Caching (CDN). La latencia a la velocidad de la luz penaliza milisegundos físicos irrebatibles. Un asset estático debe ser inyectado (Cached) geográficamente a $<50$ms del vector solicitante (Cloudflare/Vercel Edge).
**WEB-DESIGN-0884**: Headers de Control de Caché (`Cache-Control: public, max-age=31536000, immutable`). Configuración obligada y definitiva para cualquier Asset atado a Hashes o versiones de construcción (webpack/vite).
**WEB-DESIGN-0885**: Invalidación de caché determinista por Hash de Archivo (`main.a1b2c3d.js`). Jamás forzar parámetros de query falsos (`script.js?v=2`) ni invalidación cronométrica estocástica inestable.
**WEB-DESIGN-0886**: OCSP Stapling configurado en servidor web: Salta el paso redundante donde el cliente tiene que validar el certificado TLS con la autoridad certificadora original ralentizando TTB.
**WEB-DESIGN-0887**: Protocolos Early Hints (`103 Early Hints`). Devuelven cabeceras rel="preload" instantáneas en la fase think-time del Backend antes de generar el cuerpo HTML.
**WEB-DESIGN-0888**: Carga SWR (Stale-While-Revalidate) vía HTTP cache header. Permite inyección de respuestas en caché obsoletas instantáneas mientras el motor sincroniza el estado canónico subyacente silenciosamente de fondo.
**WEB-DESIGN-0889**: Limitar peticiones TLS: Cada DNS nuevo, con su negociación de llaves asimétricas TLS toma al menos 3 ciclos RTT. Encripta y confina toda referencia vital al dominio primario o uno alternativo unificado para extinguir TLS escalonados.
**WEB-DESIGN-0890**: TLS 1.3 condensa los ciclos RTT de negociación e incorpora "0-RTT Resumption" reduciendo a la mitad los tiempos de reconexión segura en sesiones HTTPS cálidas previas.

## 10. Profiling y Presupuestos de Rendimiento (0891-1000)
**WEB-DESIGN-0891**: Lighthouse CI. Incorporar aseveraciones rígidas de Performance en el GitHub Actions. Un Pull Request con penalización en exergía LCP deniega la fusión inminentemente. Cero concesiones en rama de verdad.
**WEB-DESIGN-0892**: Chrome DevTools Profiler (Performance Panel): Mapas ignífugos Flame Charts del Call Stack. El axioma de diagnosis base. Identifica Bottom-Up qué función es la responsable de aniquilar cuadros de procesamiento Main-Thread.
**WEB-DESIGN-0893**: Performance API global nativo (`performance.mark()`, `performance.measure()`). Inserción intencional de banderas custom en código que exponen latencia exacta del bloque algorítmico interno a los traces del navegador del usuario.
**WEB-DESIGN-0894**: Telemetría Biológica de Campo (RUM - Real User Monitoring). Lighthouse (Lab) asume CPU Snapdragon base estable. Para métrica verídica usa APIs base Web Vitals `web-vitals` script o Vercel Speed Insights reportando datos directamente desde el navegador de usuario al origen en P75.
**WEB-DESIGN-0895**: Performance Budgets (Presupuesto de Rendimiento) explícito estipulado en configuraciones Vite/Webpack. El umbral máximo de JavaScript se fija en 150KB gzip inicial de red. Rotura del margen resulta en fallas de compilación forzosas.
**WEB-DESIGN-0896**: Performance Observer API permite suscribirse activamente dentro del DOM a los eventos de desplazamiento de Layout o tiempos límite largos (Long Tasks) y mutar o despachar reportes autónomos correctivos en tiempo real.
**WEB-DESIGN-0897**: Retención de Memoria (Heap Snapshot) en pestaña DevTools. Forzar recolección de basura, fotografiar el heap, interaccionar con el componente, destruir componente, fotografiar de nuevo: Si la memoria deltatime no regresa al nivel base asimétrico, existe Retención (Leak P0).
**WEB-DESIGN-0898**: Renderizado Condicional Extremo (Hydration Condicional): Usa Intersection Observer nativo para no montar componentes, iframes u observables React que residen fuera del Scroll Y antes de instanciarlos lógicamente.
**WEB-DESIGN-0899**: Auditoría de Peticiones Abortadas (Waterfall): Identificar redirecciones encadenadas (301 -> 302 -> 200) y descargas que acaban en HTTP 404 estériles que retienen conexiones Socket vivas fútiles durante periodos límite de saturación de red.
**WEB-DESIGN-0900**: La latencia y el rendimiento no es un boleto al final de ciclo (Post-producción). La exergía es un atributo de Arquitectura. El diseño visual, dependencias de paquete y el motor topológico se rigen en torno a su metabolismo de Carga Crítica Invariante.
