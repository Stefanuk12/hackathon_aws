import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  server: { host: true, fs: { allow: [".."] } }, // host: test on phones over LAN; allow: read ../contracts
  build: {
    rollupOptions: {
      input: {
        player: resolve(__dirname, "index.html"),
        host: resolve(__dirname, "host.html"),
      },
    },
  },
});
