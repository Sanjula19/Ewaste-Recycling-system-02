import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Independent frontend for Component 1. Fixed on 5176 so it never collides
// with component-2 (5174), component-3 (3000), component-4 (5175), the
// gateway (8080), or the common dashboard (3010).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5176,
    strictPort: true,
  },
  preview: {
    port: 5176,
    strictPort: true,
  },
});
