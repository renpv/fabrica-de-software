import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach } from "vitest";
import { servidor } from "./servidor";

// O Mantine pede matchMedia e ResizeObserver, que o jsdom não tem.
window.matchMedia ??= ((consulta: string) => ({
  matches: false,
  media: consulta,
  onchange: null,
  addEventListener: () => {},
  removeEventListener: () => {},
  addListener: () => {},
  removeListener: () => {},
  dispatchEvent: () => false,
})) as typeof window.matchMedia;

globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Liga já na carga do setup: o openapi-fetch guarda o `fetch` global ao ser importado.
servidor.listen({ onUnhandledFrame: "error" });
afterEach(() => {
  cleanup();
  servidor.resetHandlers();
});
afterAll(() => servidor.close());
