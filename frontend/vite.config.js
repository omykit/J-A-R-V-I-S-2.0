import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],

  // The gateway's CORS allow-list is localhost:3000 / 19006 / 127.0.0.1:3000
  // (services/gateway/gateway/config.py). Vite's default 5173 is rejected with
  // HTTP 400 and no allow-origin header, so every request from the browser
  // would fail. Serving on 3000 makes the frontend a permitted origin with no
  // backend change.
  //
  // strictPort matters: without it Vite silently falls back to 3001 when 3000
  // is busy, which is NOT in the allow-list, and the failure would look like a
  // broken backend rather than a taken port.
  server: {
    port: 3000,
    strictPort: true,
  },
})