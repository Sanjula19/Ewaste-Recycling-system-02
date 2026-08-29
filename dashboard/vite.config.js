import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Common dashboard shell — independent of every component's own frontend
// build. Fixed on 3010 so it never collides with the component ports
// (5174, 3000, 5175) or the gateway/backends (8080, 8001-8004).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3010,
    strictPort: true,
  },
  preview: {
    port: 3010,
    strictPort: true,
  },
});
