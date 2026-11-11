import createClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./schema";

function lerCookie(nome: string): string | null {
  const prefixo = `${nome}=`;
  for (const parte of document.cookie.split(";")) {
    const limpo = parte.trim();
    if (limpo.startsWith(prefixo)) return decodeURIComponent(limpo.slice(prefixo.length));
  }
  return null;
}

// O Django só aceita escrita com o token do cookie `csrftoken` repetido neste cabeçalho.
const middlewareCsrf: Middleware = {
  onRequest({ request }) {
    if (!["GET", "HEAD", "OPTIONS"].includes(request.method.toUpperCase())) {
      const token = lerCookie("csrftoken");
      if (token) request.headers.set("X-CSRFToken", token);
    }
    return request;
  },
};

export const api = createClient<paths>({
  baseUrl: window.location.origin,
  credentials: "include",
});

api.use(middlewareCsrf);

/** Mensagem do back-end (`detail`) quando houver; senão, a mensagem padrão. */
export function mensagemDeErro(erro: unknown, padrao: string): string {
  if (erro && typeof erro === "object" && "detail" in erro && typeof erro.detail === "string") {
    return erro.detail;
  }
  return padrao;
}
