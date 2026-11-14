import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // MapLibre 6 starts a module worker relative to its own file; pre-bundling moves that file.
  optimizeDeps: { exclude: ['maplibre-gl'] },
  test: {
    environment: 'node',
  },
})
