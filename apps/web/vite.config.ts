import { svelteTesting } from '@testing-library/svelte/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [tailwindcss(), svelteTesting(), sveltekit()],
  optimizeDeps: {
    exclude: ['@lucide/svelte'],
  },
  build: {
    // Performance budget: JS < 150 KB gz.
    // No manualChunks: object form breaks Vite 8 Rolldown; function form is deprecated.
    reportCompressedSize: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{js,ts}'],
    // Coverage is only computed when `--coverage` is passed (pnpm test:coverage /
    // the ci-web coverage job); a plain `pnpm test` stays fast. The floor guards
    // the schema-sensitive client surface (#780, audit Q4/Q5): the API modules and
    // the offline/auth client are where a silent regression would break real user
    // flows. Thresholds are set a few points below the current numbers so they act
    // as a non-regression floor, not a moving target — raise them as coverage grows.
    coverage: {
      provider: 'v8',
      include: ['src/lib/api/**/*.ts', 'src/lib/offline/**/*.ts'],
      exclude: ['**/*.{test,spec}.{js,ts}', '**/*.d.ts'],
      reporter: ['text-summary', 'text'],
      thresholds: {
        statements: 69,
        branches: 59,
        functions: 64,
        lines: 70,
      },
    },
  },
});
