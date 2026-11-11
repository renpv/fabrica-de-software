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
});
