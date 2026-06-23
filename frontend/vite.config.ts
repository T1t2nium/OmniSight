import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * Suppress noisy Vite WebSocket proxy errors that occur when the
 * backend isn't running yet. The frontend wsClient already handles
 * reconnection with exponential backoff.
 */
function suppressWsProxyError(): Plugin {
  return {
    name: 'suppress-ws-proxy-error',
    configureServer() {
      const originalError = console.error;
      console.error = (...args: unknown[]) => {
        const first = String(args[0] || '');
        if (first.includes('ws proxy socket error')) return;
        originalError.apply(console, args);
      };
    },
  };
}

export default defineConfig({
  plugins: [react(), suppressWsProxyError()],
  server: {
    port: 5173,
    proxy: {
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
});
