import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// CORTEX Unified Substrate — v0.3.2b1 Configuration
export default defineConfig({
  output: 'static',
  integrations: [
    react(),
  ],
});
