import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import type { ReactNode } from "react";
import { useSessao } from "../sessao/useSessao";
import { servidor } from "../testes/servidor";
import { ErroDeApi, chamar, deveTentarDeNovo } from "./chamar";
import { api } from "./cliente";

const sessao = { usuario: "ana", dono: { id: "1", nome: "Central" } };

function novoCliente() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function semear(qc: QueryClient) {
  qc.setQueryData(["sessao"], sessao);
  qc.setQueryData(["contas"], [{ id: "da-ana" }]);
  qc.setQueryData(["projetos"], [{ id: "da-ana" }]);
}

describe("chamar: erros", () => {
  it("5xx com detail mostra o detail do back-end", async () => {
    servidor.use(
      http.get("/api/contas-agente/", () =>
        HttpResponse.json({ detail: "O GitLab recusou o token. Gere outro." }, { status: 502 }),
      ),
    );
    await expect(chamar(novoCliente(), () => api.GET("/api/contas-agente/"))).rejects.toThrow(
      "O GitLab recusou o token. Gere outro.",
    );
  });

  it("5xx sem detail usa a mensagem genérica", async () => {
    servidor.use(
      http.get("/api/contas-agente/", () => new HttpResponse("<html>erro</html>", { status: 500 })),
    );
    await expect(chamar(novoCliente(), () => api.GET("/api/contas-agente/"))).rejects.toThrow(
      "O servidor teve um problema. Tente de novo em instantes.",
    );
  });
});

describe("deveTentarDeNovo", () => {
  it("não repete resposta do servidor (ErroDeApi)", () => {
    expect(deveTentarDeNovo(0, new ErroDeApi("x"))).toBe(false);
  });
  it("repete falha de rede uma vez só", async () => {
    servidor.use(http.get("/api/contas-agente/", () => HttpResponse.error()));
    const erro = await chamar(novoCliente(), () => api.GET("/api/contas-agente/")).catch((e) => e);
    expect(deveTentarDeNovo(0, erro)).toBe(true);
    expect(deveTentarDeNovo(1, erro)).toBe(false);
  });
});

describe("chamar: sessão perdida", () => {
  it.each([401, 403])("no %i limpa o cache de dados e zera a sessão", async (status) => {
    servidor.use(http.get("/api/contas-agente/", () => HttpResponse.json({}, { status })));
    const qc = novoCliente();
    semear(qc);
    await expect(chamar(qc, () => api.GET("/api/contas-agente/"))).rejects.toThrow("Sua sessão expirou");
    expect(qc.getQueryData(["sessao"])).toBeNull();
    expect(qc.getQueryData(["contas"])).toBeUndefined();
    expect(qc.getQueryData(["projetos"])).toBeUndefined();
  });
});

describe("useSessao e o cache", () => {
  function envolver(qc: QueryClient) {
    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    );
  }

  it("um novo login não herda dados do usuário anterior", async () => {
    servidor.use(
      http.post("/api/sessao/", () => HttpResponse.json({ usuario: "bia", dono: { id: "2", nome: "Outra" } })),
    );
    const qc = novoCliente();
    semear(qc);
    const { result } = renderHook(() => useSessao(), { wrapper: envolver(qc) });
    await act(() => result.current.entrar("bia", "senha"));
    expect(qc.getQueryData(["contas"])).toBeUndefined();
    expect(qc.getQueryData(["projetos"])).toBeUndefined();
    expect((qc.getQueryData(["sessao"]) as typeof sessao).usuario).toBe("bia");
  });

  it.each([401, 403])("sair com a sessão já expirada (%i) limpa tudo e zera a sessão", async (status) => {
    servidor.use(http.delete("/api/sessao/", () => HttpResponse.json({}, { status })));
    const qc = novoCliente();
    semear(qc);
    const { result } = renderHook(() => useSessao(), { wrapper: envolver(qc) });
    await act(() => result.current.sair());
    await waitFor(() => expect(qc.getQueryData(["sessao"])).toBeNull());
    expect(qc.getQueryData(["contas"])).toBeUndefined();
    expect(result.current.erroAoSair).toBeNull();
  });
});

describe("cabeçalho CSRF", () => {
  afterEach(() => {
    document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  });

  it("POST, PATCH e DELETE mandam X-CSRFToken lido do cookie; GET não manda", async () => {
    document.cookie = "csrftoken=token-do-cookie";
    const vistos: Record<string, string | null> = {};
    const anotar = (metodo: string) => ({ request }: { request: Request }) => {
      vistos[metodo] = request.headers.get("X-CSRFToken");
      return HttpResponse.json({});
    };
    servidor.use(
      http.get("/api/contas-agente/", anotar("GET")),
      http.post("/api/predefinicoes/padrao/", anotar("POST")),
      http.patch("/api/predefinicoes/p1/", anotar("PATCH")),
      http.delete("/api/predefinicoes/p1/", anotar("DELETE")),
    );
    await api.GET("/api/contas-agente/");
    await api.POST("/api/predefinicoes/padrao/", { body: { executor: "a", revisor: "b" } });
    await api.PATCH("/api/predefinicoes/{id}/", { params: { path: { id: "p1" } }, body: {} });
    await api.DELETE("/api/predefinicoes/{id}/", { params: { path: { id: "p1" } } });
    expect(vistos).toEqual({
      GET: null,
      POST: "token-do-cookie",
      PATCH: "token-do-cookie",
      DELETE: "token-do-cookie",
    });
  });
});
