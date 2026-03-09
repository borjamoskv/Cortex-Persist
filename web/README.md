# Cortex Persist Web Frontend
> Sovereign State OS

Frontend inmutable diseñado bajo el paradigma **Industrial Noir 2026**.

## 🚀 Arquitectura
- **Framework:** Vite + React (O(1) dev server) 
- **Estética:** Industrial Noir (Deep Blacks, Cyber Lime, Glassmorphism, Semantic Springs <200ms).
- **Entropía:** Cero componentes genéricos. Todo es custom CSS variables.

## 🛠️ Desarrollo Local
```bash
npm install
npm run dev
```

## 🌐 Despliegue en Cloudflare Pages
Garantiza O(1) distribuyendo el frontend globalmente conectado a la rama `main`.

1. Conecta tu fork/repositorio a Cloudflare Pages.
2. **Framework preset:** `Vite`
3. **Build command:** `npm run build`
4. **Build output directory:** `dist`
5. _Root directory (Si aplica):_ `/web`

> 💡 **[SOVEREIGN TIP]** Implementa cabeceras CSP rígidas en Cloudflare para lograr el 100% de inmunidad a ataques de inyección, en sincronía con tu matriz de seguridad 6/6.
