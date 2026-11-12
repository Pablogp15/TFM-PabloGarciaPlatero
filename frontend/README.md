# Frontend de MiniPaint AI

Aplicación web en React 19 + TypeScript + Vite.

## Estructura

```
src/
├── app/            # router, providers y layout
├── pages/          # una página por ruta
├── features/       # lógica por dominio (se añade en las siguientes fases)
├── components/     # componentes reutilizables (se añade en las siguientes fases)
├── lib/            # cliente HTTP, query client y utilidades
└── styles/         # estilos globales
```

## Comandos

```bash
npm install
npm run dev          # http://localhost:5173
npm run build
npm run lint
npm run format
```

El servidor de desarrollo redirige `/api` a `http://localhost:8000`.
