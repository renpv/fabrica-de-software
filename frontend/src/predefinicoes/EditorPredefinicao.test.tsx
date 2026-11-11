import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { renderizarApp } from "../testes/renderizar";
import { servidor } from "../testes/servidor";

const sessao = { usuario: "ana", dono: { id: "1", nome: "Central" } };
const AUTO = "anterior_concluida";

function contaApi(id: string, nome: string, tipo: string) {
  return {
    id,
    nome,
    tipo,
    cliente: null,
    config: {},
    limite_simultaneo: 1,
    status: "ok",
    ultimo_teste_em: null,
    ultimo_teste_mensagem: "",
    tem_credenciais: true,
  };
}

const CONTA_CURSOR = "11111111-1111-4111-8111-111111111111";
const CONTA_CLAUDE = "22222222-2222-4222-8222-222222222222";

const etapasPadrao = [
  { chave: "publicar_tasks", papel: { tipo: "central" }, gatilho: AUTO },
  { chave: "implementar", papel: { tipo: "conta", conta_id: CONTA_CURSOR }, gatilho: AUTO },
  { chave: "revisar", papel: { tipo: "conta", conta_id: CONTA_CLAUDE }, gatilho: AUTO },
  { chave: "merge", papel: { tipo: "central" }, gatilho: AUTO },
  { chave: "promover", papel: { tipo: "humano" }, gatilho: "decisao_humana" },
];

const predefinicao = {
  id: "p1",
  nome: "Padrão",
  descricao: "",
  metodo: "superpowers",
  etapas: etapasPadrao,
  merge_autonomo: true,
};

function projeto(id: string, predefinicaoId: string) {
  return {
    id,
    nome: `Projeto ${id}`,
    conexao: "c1",
    repositorio_caminho: `acme/${id}`,
    cliente: null,
    predefinicao: predefinicaoId,
    ativo: true,
  };
}

function preparar(projetos: unknown[] = []) {
  servidor.use(
    http.get("/api/sessao/", () => HttpResponse.json(sessao)),
    http.get("/api/predefinicoes/", () => HttpResponse.json([predefinicao])),
    http.get("/api/projetos/", () => HttpResponse.json(projetos)),
    http.get("/api/contas-agente/", () =>
      HttpResponse.json([contaApi(CONTA_CURSOR, "Cursor da Ana", "cursor"), contaApi(CONTA_CLAUDE, "Claude da Ana", "claude")]),
    ),
    http.get("/api/tipos-de-agente/", () =>
      HttpResponse.json([
        { tipo: "cursor", nome: "Cursor", etiqueta: "cursor", modelos_sugeridos: ["composer-2", "gpt-5"], campos: [], guia: [] },
        { tipo: "claude", nome: "Claude", etiqueta: "claude", modelos_sugeridos: ["claude-opus-5"], campos: [], guia: [] },
      ]),
    ),
    http.get("/api/etapas-e-gatilhos/", () =>
      HttpResponse.json({
        etapas: [
          { chave: "publicar_tasks", rotulo: "Publicar as tasks" },
          { chave: "implementar", rotulo: "Implementar" },
          { chave: "revisar", rotulo: "Revisar" },
          { chave: "merge", rotulo: "Fazer o merge" },
          { chave: "promover", rotulo: "Promover para produção" },
        ],
        gatilhos: [
          { chave: AUTO, rotulo: "Quando a etapa anterior terminar" },
          { chave: "webhook", rotulo: "Quando chegar um webhook" },
          { chave: "temporizador", rotulo: "Depois de um tempo" },
          { chave: "decisao_humana", rotulo: "Quando uma pessoa decidir" },
        ],
        metodos: [{ chave: "superpowers", rotulo: "superpowers" }],
      }),
    ),
  );
}

async function abrirEditor(usuario: ReturnType<typeof userEvent.setup>) {
  const cartao = (await screen.findByText("Padrão")).closest("[data-predefinicao]") as HTMLElement;
  await usuario.click(within(cartao).getByRole("button", { name: "Editar" }));
  return await screen.findByRole("dialog");
}

function etapaNoEditor(editor: HTMLElement, chave: string) {
  return editor.querySelector(`[data-etapa="${chave}"]`) as HTMLElement;
}

describe("Predefinições", () => {
  it("criar a partir do padrão pede executor e revisor", async () => {
    preparar();
    let corpo: unknown = null;
    servidor.use(
      http.post("/api/predefinicoes/padrao/", async ({ request }) => {
        corpo = await request.json();
        return HttpResponse.json(predefinicao, { status: 201 });
      }),
    );
    const usuario = userEvent.setup();
    renderizarApp("/predefinicoes");

    await usuario.click(await screen.findByRole("button", { name: "Criar a partir do Padrão" }));
    const dialogo = await screen.findByRole("dialog");
    const criar = within(dialogo).getByRole("button", { name: "Criar" });
    expect(criar).toBeDisabled();
    await usuario.selectOptions(within(dialogo).getByLabelText("Executor"), "Cursor da Ana");
    await usuario.selectOptions(within(dialogo).getByLabelText("Revisor"), "Claude da Ana");
    await usuario.click(criar);

    await waitFor(() => expect(corpo).toEqual({ executor: CONTA_CURSOR, revisor: CONTA_CLAUDE }));
  });

  it("promover só oferece humano", async () => {
    preparar();
    const usuario = userEvent.setup();
    renderizarApp("/predefinicoes");
    const editor = await abrirEditor(usuario);

    const papelPromover = within(etapaNoEditor(editor, "promover")).getByLabelText("Papel");
    expect(within(papelPromover).getAllByRole("option").map((o) => o.textContent)).toEqual(["Humano"]);
    const papelImplementar = within(etapaNoEditor(editor, "implementar")).getByLabelText("Papel");
    expect(within(papelImplementar).getAllByRole("option").map((o) => o.textContent)).toEqual(["Conta de agente"]);
  });

  it("modelo sugere os do tipo da conta", async () => {
    preparar();
    const usuario = userEvent.setup();
    renderizarApp("/predefinicoes");
    const editor = await abrirEditor(usuario);

    const etapa = etapaNoEditor(editor, "implementar");
    const modelo = within(etapa).getByLabelText("Modelo") as HTMLInputElement;
    const lista = editor.ownerDocument.getElementById(modelo.getAttribute("list") as string) as HTMLElement;
    expect(Array.from(lista.querySelectorAll("option")).map((o) => o.getAttribute("value"))).toEqual(["composer-2", "gpt-5"]);

    await usuario.selectOptions(within(etapa).getByLabelText("Conta"), "Claude da Ana");
    const lista2 = editor.ownerDocument.getElementById(modelo.getAttribute("list") as string) as HTMLElement;
    expect(Array.from(lista2.querySelectorAll("option")).map((o) => o.getAttribute("value"))).toEqual(["claude-opus-5"]);
  });

  it("mostra o aviso de N projetos ao salvar", async () => {
    preparar([projeto("a", "p1"), projeto("b", "p1"), projeto("c", "outra")]);
    let corpo: { etapas: { chave: string }[] } | null = null;
    servidor.use(
      http.patch("/api/predefinicoes/p1/", async ({ request }) => {
        corpo = (await request.json()) as { etapas: { chave: string }[] };
        return HttpResponse.json(predefinicao);
      }),
    );
    const usuario = userEvent.setup();
    renderizarApp("/predefinicoes");
    const editor = await abrirEditor(usuario);

    expect(within(editor).getByText("Vale na hora para 2 projeto(s), a partir da próxima etapa de cada um.")).toBeInTheDocument();
    await usuario.click(within(editor).getByRole("button", { name: "Salvar" }));
    await waitFor(() => expect(corpo?.etapas.map((e) => e.chave)).toEqual(etapasPadrao.map((e) => e.chave)));
  });

  it("erro do servidor aparece na etapa", async () => {
    preparar();
    servidor.use(
      http.patch("/api/predefinicoes/p1/", () =>
        HttpResponse.json(
          { etapas: ["Etapa revisar: conta não encontrada. Escolha uma das suas contas."] },
          { status: 400 },
        ),
      ),
    );
    const usuario = userEvent.setup();
    renderizarApp("/predefinicoes");
    const editor = await abrirEditor(usuario);

    await usuario.click(within(editor).getByRole("button", { name: "Salvar" }));
    const etapa = etapaNoEditor(editor, "revisar");
    expect(await within(etapa).findByText("Etapa revisar: conta não encontrada. Escolha uma das suas contas.")).toBeInTheDocument();
    expect(within(etapaNoEditor(editor, "implementar")).queryByText(/conta não encontrada/)).toBeNull();
  });
});
