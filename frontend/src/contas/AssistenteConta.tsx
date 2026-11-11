import {
  Alert,
  Anchor,
  Button,
  Group,
  List,
  Modal,
  NativeSelect,
  NumberInput,
  PasswordInput,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { useState } from "react";
import {
  type Cliente,
  type Conta,
  ErroDeApi,
  type ResultadoTeste,
  type TipoDeAgente,
  useSalvarConta,
  useTestarConta,
  useTestarDados,
} from "./api";

type Props = {
  tipos: TipoDeAgente[];
  clientes: Cliente[];
  /** Presente na edição: o assistente abre direto no passo 2, com o tipo fixo. */
  conta?: Conta;
  onFechar: () => void;
};

const MANTER = "Deixe em branco para manter a credencial salva.";

export function AssistenteConta({ tipos, clientes, conta, onFechar }: Props) {
  const edicao = Boolean(conta);
  const [passo, setPasso] = useState(edicao ? 2 : 1);
  const [tipo, setTipo] = useState<TipoDeAgente | null>(tipos.find((t) => t.tipo === conta?.tipo) ?? null);
  const [nome, setNome] = useState(conta?.nome ?? "");
  const [cliente, setCliente] = useState(conta?.cliente ?? "");
  const [limite, setLimite] = useState<number | string>(conta?.limite_simultaneo ?? 1);
  const [segredos, setSegredos] = useState<Record<string, string>>({});
  const [resultado, setResultado] = useState<ResultadoTeste | null>(null);

  const testarDados = useTestarDados();
  const testarSalva = useTestarConta();
  const salvar = useSalvarConta(conta?.id);

  const preenchidos = Object.fromEntries(Object.entries(segredos).filter(([, v]) => v.trim() !== ""));
  const trocouSegredo = Object.keys(preenchidos).length > 0;
  const obrigatoriosOk = (tipo?.campos ?? []).every(
    (c) => !c.obrigatorio || !c.secreto || edicao || (segredos[c.chave] ?? "").trim() !== "",
  );
  const passo2Pronto = nome.trim() !== "" && obrigatoriosOk && Number(limite) >= 1;

  const aguardandoRunner = resultado?.status === "aguardando_runner";
  // Na edição sem segredo novo, a credencial salva já foi testada antes: salvar é liberado.
  const podeSalvar = Boolean(resultado?.ok || aguardandoRunner) || (edicao && !trocouSegredo);

  const erroTeste = testarDados.error ?? testarSalva.error;
  const erroSalvar = salvar.error;

  function alterar(depois: () => void) {
    setResultado(null);
    testarDados.reset();
    depois();
  }

  async function testar() {
    if (!tipo) return;
    try {
      const r =
        conta && !trocouSegredo
          ? await testarSalva.mutateAsync(conta.id)
          : await testarDados.mutateAsync({ tipo: tipo.tipo, credenciais: preenchidos });
      setResultado(r);
    } catch {
      setResultado(null);
    }
  }

  async function gravar() {
    if (!tipo) return;
    try {
      await salvar.mutateAsync({
        nome: nome.trim(),
        tipo: tipo.tipo,
        cliente: cliente || null,
        limite_simultaneo: Number(limite),
        ...(trocouSegredo || !edicao ? { credenciais: preenchidos } : {}),
      });
      onFechar();
    } catch {
      // o erro aparece pelo estado da mutação
    }
  }

  const campos = erroSalvar instanceof ErroDeApi ? erroSalvar.campos : {};
  const doCampo = (chave: string) => campos[chave]?.join(" ");
  const errosSemCampo = Object.entries(campos)
    .filter(([c]) => !["nome", "cliente", "limite_simultaneo"].includes(c))
    .flatMap(([, v]) => v);

  return (
    <Modal opened onClose={onFechar} title={edicao ? "Editar conta" : "Nova conta"} size="lg" centered>
      {passo === 1 && (
        <Stack>
          <Text fw={500}>Passo 1 de 3: escolha o tipo de agente</Text>
          {tipos.map((t) => (
            <Button
              key={t.tipo}
              variant="default"
              justify="flex-start"
              onClick={() => {
                setTipo(t);
                setPasso(2);
              }}
            >
              {t.nome}
            </Button>
          ))}
        </Stack>
      )}

      {passo === 2 && tipo && (
        <Stack>
          <Text fw={500}>Passo 2 de 3: {tipo.nome}</Text>
          <List type="ordered" spacing="xs">
            {tipo.guia.map((g) => (
              <List.Item key={g.texto}>
                {g.texto}
                {g.link && (
                  <>
                    {" "}
                    <Anchor href={g.link} target="_blank" rel="noreferrer noopener">
                      Abrir em nova aba
                    </Anchor>
                  </>
                )}
              </List.Item>
            ))}
          </List>
          <TextInput
            label="Nome"
            required
            value={nome}
            error={doCampo("nome")}
            onChange={(e) => alterar(() => setNome(e.currentTarget.value))}
          />
          {tipo.campos.map((c) =>
            c.secreto ? (
              <PasswordInput
                key={c.chave}
                label={c.rotulo}
                required={c.obrigatorio && !edicao}
                description={edicao ? MANTER : c.ajuda}
                autoComplete="off"
                value={segredos[c.chave] ?? ""}
                onChange={(e) => {
                  const valor = e.currentTarget.value;
                  alterar(() => setSegredos((s) => ({ ...s, [c.chave]: valor })));
                }}
              />
            ) : (
              <TextInput
                key={c.chave}
                label={c.rotulo}
                required={c.obrigatorio}
                description={c.ajuda}
                value={segredos[c.chave] ?? ""}
                onChange={(e) => {
                  const valor = e.currentTarget.value;
                  alterar(() => setSegredos((s) => ({ ...s, [c.chave]: valor })));
                }}
              />
            ),
          )}
          <NativeSelect
            label="Cliente"
            value={cliente}
            error={doCampo("cliente")}
            onChange={(e) => setCliente(e.currentTarget.value)}
            data={[{ value: "", label: "Sua (sem cliente)" }, ...clientes.map((c) => ({ value: c.id, label: c.nome }))]}
          />
          <NumberInput
            label="Limite simultâneo"
            description="Quantas tarefas esta conta pode executar ao mesmo tempo."
            min={1}
            allowDecimal={false}
            value={limite}
            error={doCampo("limite_simultaneo")}
            onChange={setLimite}
          />
          <Group justify="space-between">
            {edicao ? <span /> : <Button variant="default" onClick={() => setPasso(1)}>Voltar</Button>}
            <Button disabled={!passo2Pronto} onClick={() => setPasso(3)}>
              Continuar
            </Button>
          </Group>
        </Stack>
      )}

      {passo === 3 && tipo && (
        <Stack>
          <Text fw={500}>Passo 3 de 3: teste a conexão</Text>
          {erroTeste && (
            <Alert color="red" role="alert">
              {erroTeste.message}
              {erroTeste instanceof ErroDeApi &&
                Object.values(erroTeste.campos)
                  .flat()
                  .map((m) => ` ${m}`)}
            </Alert>
          )}
          {resultado && (
            <Alert color={resultado.ok ? "green" : aguardandoRunner ? "yellow" : "red"} role="status">
              {resultado.mensagem}
              {aguardandoRunner && " Você pode salvar agora e a conta fica pronta depois."}
            </Alert>
          )}
          {erroSalvar && (
            <Alert color="red" role="alert">
              {erroSalvar.message}
              {errosSemCampo.map((m) => ` ${m}`)}
            </Alert>
          )}
          <Group justify="space-between">
            <Button variant="default" onClick={() => setPasso(2)}>
              Voltar
            </Button>
            <Group>
              <Button
                variant="default"
                loading={testarDados.isPending || testarSalva.isPending}
                onClick={testar}
              >
                Testar conexão
              </Button>
              <Button disabled={!podeSalvar} loading={salvar.isPending} onClick={gravar}>
                Salvar
              </Button>
            </Group>
          </Group>
        </Stack>
      )}
    </Modal>
  );
}
