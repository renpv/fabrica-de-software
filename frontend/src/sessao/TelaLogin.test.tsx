import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { renderizarApp } from "../testes/renderizar";
import { servidor } from "../testes/servidor";

const sessao = { usuario: "ana", dono: { id: "1", nome: "Central" } };

async function preencherEEnviar(senha: string) {
  const usuario = userEvent.setup();
  await usuario.type(await screen.findByLabelText(/^Usuário/), "ana");
  await usuario.type(screen.getByLabelText(/^Senha/), senha);
  await usuario.click(screen.getByRole("button", { name: "Entrar" }));
}

describe("TelaLogin", () => {
  it("entra e vai para /contas", async () => {
    servidor.use(http.post("/api/sessao/", () => HttpResponse.json(sessao)));
    renderizarApp("/entrar");

    await preencherEEnviar("segredo");

    expect(await screen.findByRole("heading", { name: "Contas de agente" })).toBeInTheDocument();
  });

  it('mostra "Usuário ou senha incorretos." com o 400', async () => {
    servidor.use(
      http.post("/api/sessao/", () =>
        HttpResponse.json({ detail: "Usuário ou senha incorretos." }, { status: 400 }),
      ),
    );
    renderizarApp("/entrar");

    await preencherEEnviar("errada");

    expect(await screen.findByText("Usuário ou senha incorretos.")).toBeInTheDocument();
  });
});
