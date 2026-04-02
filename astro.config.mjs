import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import starlight from '@astrojs/starlight';

// CORTEX Unified Substrate — v0.3.2b1 Configuration
export default defineConfig({
  output: 'static',
  integrations: [
    react(),
    starlight({
      title: 'CORTEX Docs',
      logo: {
        src: './src/assets/logo-white.svg',
      },
      social: {
        github: 'https://github.com/borjamoskv/Cortex-Persist',
      },
      sidebar: [
        {
          label: 'Start Here',
          items: [
            { label: 'Introduction', link: '/guides/introduction' },
            { label: 'Quickstart', link: '/guides/quickstart' },
          ],
        },
        {
          label: 'Architecture',
          autogenerate: { directory: 'architecture' },
        },
        {
          label: 'Reference',
          autogenerate: { directory: 'reference' },
        },
      ],
      customCss: [
        './src/styles/custom.css',
      ],
    }),
  ],
});
