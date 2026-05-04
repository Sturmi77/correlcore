import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  build: {
    // Performance budget: JS < 150 KB gz
    reportCompressedSize: true,
    rollupOptions: {
      output: {
        manualChunks: {
          // Split vendor chunks for better caching
          svelte: ['svelte'],
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{js,ts}'],
  },
});
