import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { renderizarApp } from "../testes/renderizar";
import { servidor } from "../testes/servidor";

const sessao = { usuario: "ana", dono: { id: "1", nome: "Central" } };

const tipos = [
  {
    tipo: "claude_local",
    nome: "Claude (no seu PC)",
    etiqueta: "claude",
    modelos_sugeridos: ["opus"],
    campos: [],
    guia: [{ texto: "Faça o login do Claude Code.", link: null }],
  },
  {
    tipo: "cursor",
    nome: "Cursor",
    etiqueta: "cursor",
    modelos_sugeridos: [],
    campos: [
      {
        chave: "api_key",
        rotulo: "Chave de API do Cursor",
        secreto: true,
        ajuda: "Cole a chave.",
        obrigatorio: true,
      },
    ],
    guia: [{ texto: "Crie uma chave no painel.", link: "https://cursor.com/dashboard/api" }],
  },
];

function servidorBase() {
  servidor.use(
    http.get("/api/sessao/", () => HttpResponse.json(sessao)),
    http.get("/api/tipos-de-agente/", () => HttpResponse.json(tipos)),
    http.get("/api/clientes/", () => HttpResponse.json([{ id: "c1", nome: "Acme" }])),
    http.get("/api/contas-agente/", () => HttpResponse.json([])),
  );
}

async function abrirAssistente(nomeDoTipo: string) {
  const usuario = userEvent.setup();
  renderizarApp("/contas");
  await usuario.click(await screen.findByRole("button", { name: "Nova conta" }));
  await usuario.click(await screen.findByRole("button", { name: new RegExp(nomeDoTipo) }));
  return usuario;
}

describe("AssistenteConta", () => {
  it("salvar fica desabilitado até o teste dar ok", async () => {
    servidorBase();
    servidor.use(
      http.post("/api/contas-agente/testar/", () =>
        HttpResponse.json({ ok: true, status: "ok", mensagem: "Chave válida." }),
      ),
    );
    const usuario = await abrirAssistente("Cursor");

    await usuario.type(screen.getByLabelText(/^Nome/), "Cursor da Ana");
    await usuario.type(screen.getByLabelText(/^Chave de API do Cursor/), "key_abc");
    await usuario.click(screen.getByRole("button", { name: "Continuar" }));

    expect(screen.getByRole("button", { name: "Salvar" })).toBeDisabled();
    await usuario.click(screen.getByRole("button", { name: "Testar conexão" }));

    expect(await screen.findByText("Chave válida.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvar" })).toBeEnabled();
  });

  it("mostra a mensagem de chave recusada", async () => {
    servidorBase();
    servidor.use(
      http.post("/api/contas-agente/testar/", () =>
        HttpResponse.json({ ok: false, status: "falha", mensagem: "O Cursor recusou a chave." }),
      ),
    );
    const usuario = await abrirAssistente("Cursor");

    await usuario.type(screen.getByLabelText(/^Nome/), "Cursor da Ana");
    await usuario.type(screen.getByLabelText(/^Chave de API do Cursor/), "ruim");
    await usuario.click(screen.getByRole("button", { name: "Continuar" }));
    await usuario.click(screen.getByRole("button", { name: "Testar conexão" }));

    expect(await screen.findByText("O Cursor recusou a chave.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvar" })).toBeDisabled();
  });

  it("claude local salva com o aviso de runner", async () => {
    servidorBase();
    let corpo: unknown;
    servidor.use(
      http.post("/api/contas-agente/testar/", () =>
        HttpResponse.json({
          ok: false,
          status: "aguardando_runner",
          mensagem: "Esta conta fica pronta quando o runner do seu PC se conectar.",
        }),
      ),
      http.post("/api/contas-agente/", async ({ request }) => {
        corpo = await request.json();
        return HttpResponse.json({ id: "n1" }, { status: 201 });
      }),
    );
    const usuario = await abrirAssistente("Claude");

    await usuario.type(screen.getByLabelText(/^Nome/), "Claude da Ana");
    await usuario.click(screen.getByRole("button", { name: "Continuar" }));
    await usuario.click(screen.getByRole("button", { name: "Testar conexão" }));

    expect(await screen.findByText(/runner do seu PC se conectar/)).toBeInTheDocument();
    expect(screen.getByText(/Você pode salvar agora/)).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(corpo).toMatchObject({ tipo: "claude_local", nome: "Claude da Ana" }));
  });

  it("edição não pré-preenche o segredo", async () => {
    servidorBase();
    servidor.use(
      http.get("/api/contas-agente/", () =>
        HttpResponse.json([
          {
            id: "a1",
            nome: "Cursor da Ana",
            tipo: "cursor",
            cliente: null,
            config: {},
            limite_simultaneo: 2,
            status: "ok",
            ultimo_teste_em: null,
            ultimo_teste_mensagem: "",
            tem_credenciais: true,
          },
        ]),
      ),
    );
    const usuario = userEvent.setup();
    renderizarApp("/contas");

    await usuario.click(await screen.findByRole("button", { name: "Editar" }));

    expect(await screen.findByLabelText(/^Chave de API do Cursor/)).toHaveValue("");
    expect(screen.getByText("Deixe em branco para manter a credencial salva.")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Nome/)).toHaveValue("Cursor da Ana");
  });
});
