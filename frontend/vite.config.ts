import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

declare const process: { env: Record<string, string | undefined> };
const API_TARGET = process.env.VITE_API_PROXY || "http://127.0.0.1:8000";
const WS_TARGET = API_TARGET.replace(/^http/, "ws");

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": API_TARGET,
      "/ws": { target: WS_TARGET, ws: true },
    },
  },
});
