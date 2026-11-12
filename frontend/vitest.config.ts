import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    // jsdom aporta `document.cookie`, necesario para el token CSRF.
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    restoreMocks: true,
  },
})
