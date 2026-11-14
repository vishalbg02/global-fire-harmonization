import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // MapLibre 6 starts a module worker relative to its own file; pre-bundling moves that file.
  optimizeDeps: { exclude: ['maplibre-gl'] },
  build: {
    // maplibre-gl is one library (about 1.06 MB minified, plus its own 519 kB worker) that cannot be split
    // further; it loads only with the map. Every other chunk is under 500 kB (T-042).
    chunkSizeWarningLimit: 1100,
    rolldownOptions: {
      output: {
        // Split the map's libraries into their own chunks (T-042): each loads only with the map.
        codeSplitting: {
          groups: [
            { name: 'maplibre', test: /node_modules[\\/]maplibre-gl/ },
            { name: 'deckgl-luma', test: /node_modules[\\/]@luma\.gl/ },
            { name: 'deckgl-loaders', test: /node_modules[\\/](@loaders\.gl|@probe\.gl|@math\.gl)/ },
            { name: 'deckgl', test: /node_modules[\\/]@deck\.gl/ },
            { name: 'zrender', test: /node_modules[\\/]zrender/ },
            { name: 'echarts', test: /node_modules[\\/]echarts/ },
            { name: 'terra-draw', test: /node_modules[\\/]terra-draw/ },
          ],
        },
      },
    },
  },
  // In development the web app proxies /api to the local API (no CORS configuration needed).
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
  test: {
    environment: 'node',
  },
})
