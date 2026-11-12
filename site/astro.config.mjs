import { defineConfig } from 'astro/config';

// Served from https://tharold4096.github.io/thearchivist/ (GitHub Pages, Actions source).
export default defineConfig({
  site: 'https://tharold4096.github.io',
  base: '/thearchivist',
  trailingSlash: 'always',
  output: 'static',
  build: { format: 'directory' },
  devToolbar: { enabled: false },
});
