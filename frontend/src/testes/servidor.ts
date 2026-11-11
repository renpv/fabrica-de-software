import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";

export const handlersPadrao = [
  http.get("/api/sessao/", () =>
    HttpResponse.json({ detail: "As credenciais não foram fornecidas." }, { status: 403 }),
  ),
  http.delete("/api/sessao/", () => new HttpResponse(null, { status: 204 })),
];

export const servidor = setupServer(...handlersPadrao);
