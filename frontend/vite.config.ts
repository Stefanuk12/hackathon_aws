import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  server: { host: true }, // listen on the LAN so phones on the same wifi can join
  build: {
    rollupOptions: {
      input: {
        player: resolve(__dirname, "index.html"),
        host: resolve(__dirname, "host.html"),
      },
    },
  },
});
