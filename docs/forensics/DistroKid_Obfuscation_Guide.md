# DIRECTIVA DE OFUSCACIÓN DE CRÉDITOS: DISTROKID / SGAE / SPOTIFY

> **SYS_ID:** `borjamoskv` | **Reality Level:** `C5-REAL` | **Status:** `CONSOLIDATED`
> **Ecosistema:** Distribución Digital y Derechos de Autor (MLC / PRO / DDEX Feed)

---

## 1. Anatomía de la Fuga de PII en Música
Los agregadores y plataformas analíticas (e.g., Spotify, Apple Music, Viberate, Musixmatch) obtienen sus datos directamente de los feeds **DDEX XML** de las distribuidoras digitales. 
*   **El Vínculo Crítico:** La asociación entre tu nombre legal (`[REDACTED_LEGAL_PII]`) y tu alias (`Borja Moskv`) se origina en la sección **"Songwriter Credits"** (Créditos de Compositor/Autor).
*   **Limitación de Solución:** No puedes exigir a Spotify o Apple Music que borren esta información a través de solicitudes de privacidad estándar; responderán que los datos provienen de tu distribuidora. El cambio **debe originarse en la distribuidora** y propagarse como un "Metadata Update".

---

## 2. Protocolo de Mitigación (Fase 2)

Elige **UNA** de las siguientes rutas dependiendo de tu estrategia de retención de catálogo.

### 🔴 VÍA A: Ofuscación y Registro de Seudónimo (Recomendada - Conserva Regalías)
Esta vía oculta tu nombre legal de la vista pública manteniendo tus derechos económicos intactos.

#### Paso A.1: Registro del Seudónimo en SGAE
1. Accede a tu panel de socio de la **SGAE** (Sociedad General de Autores y Editores).
2. Solicita el registro de un **Seudónimo Artístico** oficial (e.g., `Borja Moskv`).
3. El seudónimo quedará vinculado internamente a tu cuenta de socio (con tu nombre legal y cuenta bancaria para el reparto de regalías), pero la SGAE lo utilizará en sus consultas y bases de datos públicas de obras registradas.

#### Paso A.2: Actualización de Créditos en DistroKid
1. Inicia sesión en **DistroKid**.
2. Haz clic en el **menú de herramientas** (icono de cuatro cuadrados en la esquina superior derecha).
3. Selecciona **"Enhance your music"** y luego **"Credits"** (o navega directamente a [distrokid.com/credits](https://distrokid.com/credits)).
4. Selecciona cada una de las obras de tu catálogo (ej. *Everything is fine*, *Love*, *We All Adore Kangaroos*, *Trambólico*).
5. En el menú desplegable, selecciona **"Songwriter"** (o edita el crédito existente).
6. Modifica el nombre del compositor: **Reemplaza tu nombre legal por tu seudónimo registrado** (`Borja Moskv`).
7. Haz clic en **"Save this credit"** y luego en **"Done, submit to streaming services"**.

> [!NOTE]
> La propagación a las tiendas (Spotify, Apple Music, Deezer) suele tardar entre **3 y 14 días**. Viberate y otros agregadores que scrapean estas plataformas se actualizarán automáticamente en su siguiente ciclo de barrido una vez que las plataformas de streaming muestren la metadata actualizada.

---

### ❌ VÍA B: Apoptosis de Catálogo (Takedown Total)
Esta vía elimina por completo tu música de la red para cortar de raíz cualquier leak de metadatos, a costa de perder oyentes mensuales y estadísticas históricas.

1. Accede a tu panel de **DistroKid**.
2. Haz clic en el álbum o single que deseas eliminar.
3. Ve a la parte inferior de la página de la versión y haz clic en **"Remove from all stores"**.
4. Confirma la solicitud. Las tiendas procesarán el takedown en un plazo de **48 a 72 horas**.
5. **Mitigación Futura:** Si decides volver a publicar estas canciones, asegúrate de:
   *   Crear una entidad legal intermediaria (e.g., una LLC de gestión de catálogo) que aparezca como copyright owner.
   *   Utilizar un agregador que permita ocultar por completo los nombres de los compositores de la metadata pública (algunas distribuidoras boutique/empresariales permiten enviar créditos con identificadores IPN o IPI sin exponer nombres legales al usuario final).
