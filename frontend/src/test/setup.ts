import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { server } from "./server";
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(() => vi.stubEnv("VITE_API_BASE_URL", "http://localhost:5173/api"));
afterEach(() => {
  cleanup();
  server.resetHandlers();
  vi.unstubAllEnvs();
});
afterAll(() => server.close());
