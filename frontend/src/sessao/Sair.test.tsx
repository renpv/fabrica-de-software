import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { renderizarApp } from "../testes/renderizar";
import { servidor } from "../testes/servidor";

const sessao = { usuario: "ana", dono: { id: "1", nome: "Central" } };

describe("Sair", () => {
  it("encerra a sessão e vai para /entrar", async () => {
    servidor.use(http.get("/api/sessao/", () => HttpResponse.json(sessao)));
    renderizarApp("/contas");

    await userEvent.click(await screen.findByRole("button", { name: "Sair" }));

    expect(await screen.findByRole("button", { name: "Entrar" })).toBeInTheDocument();
  });

  it("se o servidor recusar, mantém a sessão e mostra o erro", async () => {
    servidor.use(
      http.get("/api/sessao/", () => HttpResponse.json(sessao)),
      http.delete("/api/sessao/", () =>
        HttpResponse.json({ detail: "Falha ao sair." }, { status: 500 }),
      ),
    );
    renderizarApp("/contas");

    await userEvent.click(await screen.findByRole("button", { name: "Sair" }));

    expect(await screen.findByText("Falha ao sair.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Contas de agente" })).toBeInTheDocument();
  });

  it("DELETE 401: já estava deslogado, vai para /entrar", async () => {
    servidor.use(
      http.get("/api/sessao/", () => HttpResponse.json(sessao)),
      http.delete("/api/sessao/", () => HttpResponse.json({}, { status: 401 })),
    );
    renderizarApp("/contas");
    await userEvent.click(await screen.findByRole("button", { name: "Sair" }));
    expect(await screen.findByRole("button", { name: "Entrar" })).toBeInTheDocument();
  });

  it.each([401, 403])("DELETE 403 e a reconsulta da sessão dá %i: vai para /entrar", async (status) => {
    let consultas = 0;
    servidor.use(
      http.get("/api/sessao/", () =>
        ++consultas === 1 ? HttpResponse.json(sessao) : HttpResponse.json({}, { status }),
      ),
      http.delete("/api/sessao/", () => HttpResponse.json({}, { status: 403 })),
    );
    renderizarApp("/contas");
    await userEvent.click(await screen.findByRole("button", { name: "Sair" }));
    expect(await screen.findByRole("button", { name: "Entrar" })).toBeInTheDocument();
  });

  it("DELETE 403 (CSRF) com a sessão ainda ativa: continua logado e mostra o erro", async () => {
    servidor.use(
      http.get("/api/sessao/", () => HttpResponse.json(sessao)),
      http.delete("/api/sessao/", () => HttpResponse.json({}, { status: 403 })),
    );
    renderizarApp("/contas");
    await userEvent.click(await screen.findByRole("button", { name: "Sair" }));
    expect(
      await screen.findByText("Não foi possível sair. Recarregue a página e tente de novo."),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Contas de agente" })).toBeInTheDocument();
  });

  it("DELETE 403 e falha de rede na reconsulta: continua logado e mostra o erro", async () => {
    let consultas = 0;
    servidor.use(
      http.get("/api/sessao/", () => (++consultas === 1 ? HttpResponse.json(sessao) : HttpResponse.error())),
      http.delete("/api/sessao/", () => HttpResponse.json({}, { status: 403 })),
    );
    renderizarApp("/contas");
    await userEvent.click(await screen.findByRole("button", { name: "Sair" }));
    expect(
      await screen.findByText("Não foi possível sair. Recarregue a página e tente de novo."),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Contas de agente" })).toBeInTheDocument();
  });
});
