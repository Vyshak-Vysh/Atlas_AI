import { defineConfig } from "vitest/config";
import path from "node:path";

// Node environment only: these tests cover pure logic in `src/lib`
// (status mapping, navigation shape, the API client's error/refresh
// behaviour). Rendering tests would need jsdom and a component harness;
// the logic here is what silently breaks a screen when a backend enum
// changes, so it is the part worth pinning first.
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
