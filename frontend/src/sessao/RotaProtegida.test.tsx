import { screen } from "@testing-library/react";
import { renderizarApp } from "../testes/renderizar";

describe("RotaProtegida", () => {
  it("sem sessão, /contas redireciona para /entrar", async () => {
    renderizarApp("/contas");

    expect(await screen.findByRole("button", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Contas de agente" })).not.toBeInTheDocument();
  });
});
