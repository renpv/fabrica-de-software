import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { renderizarApp } from "../testes/renderizar";
import { servidor } from "../testes/servidor";

const sessao = { usuario: "ana", dono: { id: "1", nome: "Central" } };

function conexao(id: string, nome: string, tipo: "github" | "gitlab", config: unknown = {}) {
  return {
    id,
    nome,
    tipo,
    url_base: tipo === "gitlab" ? "https://gitlab.exemplo.com" : "https://api.github.com",
    config,
    status: "ok",
    ultimo_teste_mensagem: "",
    tem_credenciais: true,
  };
}

function projeto(id: string, nome: string, conferencia: unknown[]) {
  return {
    id,
    nome,
    conexao: "c1",
    repositorio_caminho: `acme/${nome}`,
    repositorio_id_externo: "42",
    repositorio_url: `https://gitlab.exemplo.com/acme/${nome}`,
    cliente: null,
    predefinicao: null,
    ativo: true,
    conferencia,
    ultima_conferencia_em: null,
    erro_ao_preparar: "",
  };
}

function item(chave: string, ok: boolean, consertavel: boolean) {
  return { chave, titulo: `Item ${chave}`, ok, mensagem: `Mensagem ${chave}`, consertavel };
}

function basico(extra: Parameters<typeof servidor.use> = []) {
  servidor.use(
    http.get("/api/sessao/", () => HttpResponse.json(sessao)),
    http.get("/api/clientes/", () => HttpResponse.json([])),
    http.get("/api/predefinicoes/", () => HttpResponse.json([])),
    ...extra,
  );
}

describe("TelaPlataformas", () => {
  it("conectar GitHub envia o manifesto para a URL de ação", async () => {
    const enviados: { action: string; method: string; manifest: string }[] = [];
    const ouvinte = (e: Event) => {
      e.preventDefault();
      const form = e.target as HTMLFormElement;
      enviados.push({
        action: form.action,
        method: form.method,
        manifest: (form.elements.namedItem("manifest") as HTMLInputElement).value,
      });
    };
    document.addEventListener("submit", ouvinte);
    try {
      let corpo: unknown = null;
      basico([
        http.get("/api/conexoes-plataforma/", () => HttpResponse.json([])),
        http.get("/api/projetos/", () => HttpResponse.json([])),
        http.post("/api/conexoes-plataforma/github/manifesto/", async ({ request }) => {
          corpo = await request.json();
          return HttpResponse.json({
            acao: "https://github.com/settings/apps/new?state=abc",
            manifesto: { name: "Fabrica Minha", url: "https://central.exemplo.com" },
          });
        }),
      ]);
      const usuario = userEvent.setup();
      renderizarApp("/plataformas");

      await usuario.click(await screen.findByRole("button", { name: "Conectar GitHub" }));
      await usuario.type(screen.getByLabelText(/Nome/), "Minha");
      await usuario.click(screen.getByRole("button", { name: "Criar App no GitHub" }));

      await waitFor(() => expect(enviados).toHaveLength(1));
      expect(corpo).toEqual({ nome: "Minha" });
      expect(enviados[0].method).toBe("post");
      expect(enviados[0].action).toBe("https://github.com/settings/apps/new?state=abc");
      expect(JSON.parse(enviados[0].manifest)).toEqual({
        name: "Fabrica Minha",
        url: "https://central.exemplo.com",
      });
    } finally {
      document.removeEventListener("submit", ouvinte);
    }
  });

  it("erro do GitLab preserva o formulário", async () => {
    basico([
      http.get("/api/conexoes-plataforma/", () => HttpResponse.json([])),
      http.get("/api/projetos/", () => HttpResponse.json([])),
      http.post("/api/conexoes-plataforma/gitlab/", () =>
        HttpResponse.json({ detail: "O GitLab recusou o token. Confira o escopo api." }, { status: 400 }),
      ),
    ]);
    const usuario = userEvent.setup();
    renderizarApp("/plataformas");

    await usuario.click(await screen.findByRole("button", { name: "Conectar GitLab" }));
    await usuario.type(screen.getByLabelText(/Nome/), "Meu GitLab");
    await usuario.type(screen.getByLabelText(/URL da instância/), "https://gitlab.exemplo.com");
    await usuario.type(screen.getByLabelText(/Token/), "segredo-123");
    await usuario.click(screen.getByRole("button", { name: "Conectar" }));

    expect(await screen.findByText("O GitLab recusou o token. Confira o escopo api.")).toBeInTheDocument();
    expect(screen.getByLabelText(/Nome/)).toHaveValue("Meu GitLab");
    expect(screen.getByLabelText(/URL da instância/)).toHaveValue("https://gitlab.exemplo.com");
    expect(screen.getByLabelText(/Token/)).toHaveValue("segredo-123");
  });

  it("novo projeto mostra a conferência", async () => {
    let corpo: unknown = null;
    basico([
      http.get("/api/conexoes-plataforma/", () => HttpResponse.json([conexao("c1", "Meu GitLab", "gitlab")])),
      http.get("/api/projetos/", () => HttpResponse.json([])),
      http.get("/api/conexoes-plataforma/c1/repositorios/", () =>
        HttpResponse.json([
          { id_externo: "41", caminho: "acme/outro", url_web: "https://x/outro" },
          { id_externo: "42", caminho: "acme/loja", url_web: "https://x/loja" },
        ]),
      ),
      http.post("/api/projetos/", async ({ request }) => {
        corpo = await request.json();
        return HttpResponse.json(
          projeto("p1", "loja", [item("etiquetas", true, false), item("webhook", false, true)]),
          { status: 201 },
        );
      }),
    ]);
    const usuario = userEvent.setup();
    renderizarApp("/plataformas");

    await usuario.click(await screen.findByRole("button", { name: "Novo projeto" }));
    await usuario.selectOptions(await screen.findByLabelText("Conexão"), "c1");
    await usuario.type(await screen.findByLabelText("Buscar repositório"), "loja");
    expect(screen.queryByRole("option", { name: "acme/outro" })).not.toBeInTheDocument();
    await usuario.selectOptions(screen.getByLabelText("Repositório"), "42");
    await usuario.click(screen.getByRole("button", { name: "Criar projeto" }));

    expect(await screen.findByText("Item etiquetas")).toBeInTheDocument();
    expect(corpo).toMatchObject({ conexao: "c1", repositorio_id_externo: "42", nome: "loja" });
    const ok = screen.getByText("Item etiquetas").closest("li") as HTMLElement;
    expect(within(ok).getByText("✓")).toBeInTheDocument();
    const falha = screen.getByText("Item webhook").closest("li") as HTMLElement;
    expect(within(falha).getByText("✗")).toBeInTheDocument();
    expect(within(falha).getByText("Mensagem webhook")).toBeInTheDocument();
  });

  it("consertar só aparece com item consertável em falha", async () => {
    let preparou = 0;
    basico([
      http.get("/api/conexoes-plataforma/", () => HttpResponse.json([conexao("c1", "Meu GitLab", "gitlab")])),
      http.get("/api/projetos/", () =>
        HttpResponse.json([
          projeto("p1", "loja", [item("a", true, true), item("b", false, true)]),
          projeto("p2", "blog", [item("a", true, true), item("b", false, false)]),
          projeto("p3", "docs", [item("a", true, true)]),
        ]),
      ),
      http.post("/api/projetos/p1/preparar/", () => {
        preparou += 1;
        return HttpResponse.json({ itens: [item("a", true, true), item("b", true, true)], conferido_em: null });
      }),
    ]);
    const usuario = userEvent.setup();
    renderizarApp("/plataformas");

    const loja = (await screen.findByText("loja")).closest("[data-projeto]") as HTMLElement;
    const blog = screen.getByText("blog").closest("[data-projeto]") as HTMLElement;
    const docs = screen.getByText("docs").closest("[data-projeto]") as HTMLElement;
    expect(within(loja).getByRole("button", { name: "Consertar" })).toBeInTheDocument();
    expect(within(blog).queryByRole("button", { name: "Consertar" })).not.toBeInTheDocument();
    expect(within(docs).queryByRole("button", { name: "Consertar" })).not.toBeInTheDocument();

    await usuario.click(within(loja).getByRole("button", { name: "Consertar" }));
    await waitFor(() => expect(preparou).toBe(1));
    await waitFor(() => expect(within(loja).queryByRole("button", { name: "Consertar" })).not.toBeInTheDocument());
  });

  it("traduz o código de erro da URL e nunca mostra o valor cru", async () => {
    basico([
      http.get("/api/conexoes-plataforma/", () => HttpResponse.json([])),
      http.get("/api/projetos/", () => HttpResponse.json([])),
    ]);
    const { unmount } = renderizarApp("/plataformas?erro=estado_invalido");
    expect(await screen.findByText(/link de conexão com o GitHub é inválido/)).toBeInTheDocument();
    unmount();

    renderizarApp("/plataformas?erro=<b>hack</b>");
    expect(await screen.findByText(/Algo deu errado ao conectar o GitHub/)).toBeInTheDocument();
    expect(screen.queryByText(/hack/)).not.toBeInTheDocument();
  });

  it("excluir conexão do GitHub avisa que o App fica e mostra o 409 do servidor", async () => {
    basico([
      http.get("/api/conexoes-plataforma/", () =>
        HttpResponse.json([conexao("g1", "Minha", "github", { installation_id: "9" })]),
      ),
      http.get("/api/projetos/", () => HttpResponse.json([])),
      http.delete("/api/conexoes-plataforma/g1/", () =>
        HttpResponse.json({ detail: "Esta conexão ainda tem projetos." }, { status: 409 }),
      ),
    ]);
    const usuario = userEvent.setup();
    renderizarApp("/plataformas");

    await usuario.click(await screen.findByRole("button", { name: "Excluir" }));
    expect(await screen.findByText(/não remove o App no GitHub/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "https://github.com/settings/apps" })).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Confirmar exclusão" }));
    expect(await screen.findByText("Esta conexão ainda tem projetos.")).toBeInTheDocument();
  });

  it("conferir depois de consertar mostra o resultado mais recente", async () => {
    basico([
      http.get("/api/conexoes-plataforma/", () => HttpResponse.json([conexao("c1", "Meu GitLab", "gitlab")])),
      http.get("/api/projetos/", () => HttpResponse.json([projeto("p1", "loja", [item("b", false, true)])])),
      http.post("/api/projetos/p1/preparar/", () =>
        HttpResponse.json({ itens: [item("b", true, true)], conferido_em: null }),
      ),
      http.post("/api/projetos/p1/conferir/", () =>
        HttpResponse.json({ itens: [item("b", false, true)], conferido_em: null }),
      ),
    ]);
    const usuario = userEvent.setup();
    renderizarApp("/plataformas");

    const loja = (await screen.findByText("loja")).closest("[data-projeto]") as HTMLElement;
    await usuario.click(within(loja).getByRole("button", { name: "Consertar" }));
    await waitFor(() => expect(within(loja).getByText("✓")).toBeInTheDocument());
    expect(within(loja).queryByRole("button", { name: "Consertar" })).not.toBeInTheDocument();

    await usuario.click(within(loja).getByRole("button", { name: "Conferir" }));
    await waitFor(() => expect(within(loja).getByText("✗")).toBeInTheDocument());
    expect(within(loja).getByRole("button", { name: "Consertar" })).toBeInTheDocument();
  });
});
