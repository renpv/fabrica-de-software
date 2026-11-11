import { screen, within } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { renderizarApp } from "../testes/renderizar";
import { servidor } from "../testes/servidor";

const sessao = { usuario: "ana", dono: { id: "1", nome: "Central" } };

function conta(id: string, nome: string, status: string, cliente: string | null) {
  return {
    id,
    nome,
    tipo: "cursor",
    cliente,
    config: {},
    limite_simultaneo: 1,
    status,
    ultimo_teste_em: null,
    ultimo_teste_mensagem: `mensagem de ${nome}`,
    tem_credenciais: true,
  };
}

describe("TelaContas", () => {
  it("a lista mostra o selo de status", async () => {
    servidor.use(
      http.get("/api/sessao/", () => HttpResponse.json(sessao)),
      http.get("/api/tipos-de-agente/", () =>
        HttpResponse.json([
          { tipo: "cursor", nome: "Cursor", etiqueta: "cursor", modelos_sugeridos: [], campos: [], guia: [] },
        ]),
      ),
      http.get("/api/clientes/", () => HttpResponse.json([{ id: "c1", nome: "Acme" }])),
      http.get("/api/contas-agente/", () =>
        HttpResponse.json([
          conta("1", "Conta A", "ok", "c1"),
          conta("2", "Conta B", "falha", null),
          conta("3", "Conta C", "aguardando_runner", null),
          conta("4", "Conta D", "nao_testada", null),
        ]),
      ),
    );
    renderizarApp("/contas");

    const linhaA = (await screen.findByText("Conta A")).closest("[data-conta]") as HTMLElement;
    expect(within(linhaA).getByText("ok")).toBeInTheDocument();
    expect(within(linhaA).getByText("Acme")).toBeInTheDocument();
    expect(within(linhaA).getByText("mensagem de Conta A")).toBeInTheDocument();
    const linhaB = screen.getByText("Conta B").closest("[data-conta]") as HTMLElement;
    expect(within(linhaB).getByText("falha")).toBeInTheDocument();
    expect(within(linhaB).getByText("Sua")).toBeInTheDocument();
    const linhaC = screen.getByText("Conta C").closest("[data-conta]") as HTMLElement;
    expect(within(linhaC).getByText("aguardando runner")).toBeInTheDocument();
    const linhaD = screen.getByText("Conta D").closest("[data-conta]") as HTMLElement;
    expect(within(linhaD).getByText("não testada")).toBeInTheDocument();
  });
});
