# PetMove — sitio listo para producción

Este archivo `index.html` es tu artefacto de Claude ("PetMove") **limpiado
para usarse como sitio real**, fuera del entorno de vista previa de
claude.ai.

## Qué se quitó y por qué

El artefacto original, tal como se sirve dentro de claude.ai, incluye un
bloque de código (`__FRAME_PREAMBLE` y todo el script que le sigue) que
solo sirve para que la página funcione **embebida en un iframe de
claude.ai**: negocia con la ventana padre por `postMessage`, restaura el
scroll, deshabilita WebRTC, etc. Ese código:

- No hace nada útil en tu propio dominio (intenta cargar módulos desde
  rutas como `/_runtime/...` que no existen fuera de claude.ai).
- Aumenta el peso de la página sin necesidad.
- No es información sensible ni una vulnerabilidad, pero tampoco pertenece
  a un sitio de producción.

Se quitó por completo. Lo que queda es exactamente tu contenido: el
`<head>` (título, fuentes, estilos) y el `<body>` (header, catálogo,
footer), verificado visualmente con una captura de pantalla para
confirmar que se ve igual.

## Por qué ya es un sitio de bajo riesgo

Revisé el HTML completo buscando los problemas típicos de seguridad antes
de publicar algo así:

- **Sin formularios ni backend**: los pedidos se hacen por enlaces
  `https://wa.me/523326374847?...`, no hay ningún dato que viaje a un
  servidor tuyo.
- **Sin JavaScript propio** (0 `<script>`, 0 `onclick`/`onerror` inline) —
  no hay superficie para inyección de scripts.
- **Sin API keys ni credenciales** embebidas en el código.
- **Sin `localStorage`/cookies** que guarden datos de clientes.
- Las imágenes están embebidas como `data:` (no dependen de un servidor de
  imágenes externo).

Por eso el `Content-Security-Policy` en `_headers` / `vercel.json` puede
ser muy estricto (`script-src` implícito en `default-src 'none'`, cero
scripts permitidos): si alguien intentara inyectar un `<script>` más
adelante (por ejemplo, a través de un comentario de terceros si agregas un
CMS), el navegador lo bloquearía.

## Cómo publicarlo (elige un hosting)

Cualquiera de estos sirve `index.html` por HTTPS gratis y lee
automáticamente el archivo `_headers` (Netlify, Cloudflare Pages) o
`vercel.json` (Vercel):

1. **Cloudflare Pages** o **Netlify** (recomendado, más simple):
   arrastra la carpeta `petmove-site/` en su panel, o conecta este repo y
   apunta el "publish directory" a `petmove-site`.
2. **Vercel**: `vercel deploy` desde esta carpeta.
3. **GitHub Pages**: funciona, pero no lee `_headers`/`vercel.json` — las
   cabeceras de seguridad no aplicarán ahí salvo que agregues Cloudflare
   delante como proxy.

Después de publicar, verifica las cabeceras con:

```
curl -sI https://tu-dominio.com | grep -i "content-security-policy\|x-frame\|strict-transport"
```

## Checklist antes de compartirlo con clientes

- [ ] Dominio propio con HTTPS activo (candado en el navegador, sin
      advertencias).
- [ ] Confirmar que el número de WhatsApp (`52 33 2637 4847`) es el
      correcto y está monitoreado.
- [ ] Probar los 7 botones "Preguntar por WhatsApp" en celular real
      (iOS y Android) y en escritorio — deben abrir WhatsApp con el
      mensaje precargado correcto por producto.
- [ ] Revisar la vista previa al compartir el link en WhatsApp/Facebook
      (Open Graph). Ahora mismo `og:image` no está puesto porque las
      imágenes están en `data:` y esas no sirven como preview social —
      si quieres una miniatura al compartir el link, sube una imagen real
      (jpg/png, hosteada) y agrégala como `og:image` en el `<head>`.
- [ ] Revisar tiempo de carga: el archivo pesa ~2.2 MB por las imágenes
      embebidas en base64. Funciona, pero convertir esas imágenes a
      archivos `.webp` reales (en vez de `data:` incrustado) bajaría
      bastante el peso y mejoraría la velocidad en celular.
- [ ] Probar en un lector de pantalla o revisar que las imágenes tengan
      texto alternativo (`alt=""`) razonable, por accesibilidad.
- [ ] Si más adelante agregas un formulario de contacto, newsletter o
      analítica (Meta Pixel, Google Analytics): nunca pongas tokens de
      acceso ni claves privadas en el HTML/JS del sitio — solo IDs
      públicos (como el Pixel ID) van en el cliente; cualquier credencial
      va en un backend o función serverless, nunca visible en el código
      fuente de la página.
