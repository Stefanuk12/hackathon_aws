import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  // host: listen on the LAN so phones on the same wifi can join.
  // fs.allow: the mock imports backend/src/shared/themes.json so both use one theme catalogue.
  server: { host: true, fs: { allow: [".."] } },
  build: {
    rollupOptions: {
      input: {
        player: resolve(__dirname, "index.html"),
        host: resolve(__dirname, "host.html"),
      },
    },
  },
});
