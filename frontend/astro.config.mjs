import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import cloudflare from '@astrojs/cloudflare';

// CORTEX Unified Substrate — v1.0.0 Configuration
export default defineConfig({
  output: 'server',
  adapter: cloudflare(),
  integrations: [
    react(),
  ],
});
