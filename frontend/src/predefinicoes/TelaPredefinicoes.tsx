import { Alert, Button, Group, Loader, Modal, NativeSelect, Paper, Stack, Text, TextInput, Title } from "@mantine/core";
import { useState } from "react";
import { mensagemComCampos } from "../api/campos";
import { EditorPredefinicao } from "./EditorPredefinicao";
import {
  type Predefinicao,
  useContas,
  useCriarPadrao,
  useDuplicar,
  usePredefinicoes,
  useProjetos,
  useRotulos,
  useTipos,
} from "./api";

function CriarPadrao({ onFechar }: { onFechar: () => void }) {
  const contas = useContas();
  const criar = useCriarPadrao();
  const [executor, setExecutor] = useState("");
  const [revisor, setRevisor] = useState("");
  const opcoes = [{ value: "", label: "Escolha uma conta" }, ...(contas.data ?? []).map((c) => ({ value: c.id, label: c.nome }))];

  return (
    <Modal opened onClose={onFechar} title="Criar a partir do Padrão" centered>
      <Stack>
        <Text size="sm">O Padrão publica as tasks, implementa, revisa, faz o merge e espera o ok para produção.</Text>
        {contas.data?.length === 0 && <Alert color="yellow">Cadastre uma conta de agente antes, na tela de contas.</Alert>}
        <NativeSelect label="Executor" data={opcoes} value={executor} onChange={(e) => setExecutor(e.currentTarget.value)} />
        <NativeSelect label="Revisor" data={opcoes} value={revisor} onChange={(e) => setRevisor(e.currentTarget.value)} />
        {(criar.error ?? contas.error) && (
          <Alert color="red" role="alert">
            {criar.error
              ? mensagemComCampos(criar.error, { rotulos: { executor: "Executor", revisor: "Revisor" } })
              : contas.error?.message}
          </Alert>
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onFechar}>
            Cancelar
          </Button>
          <Button
            disabled={!executor || !revisor}
            loading={criar.isPending}
            onClick={() => criar.mutate({ executor, revisor }, { onSuccess: onFechar })}
          >
            Criar
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function Duplicar({ predefinicao, onFechar }: { predefinicao: Predefinicao; onFechar: () => void }) {
  const duplicar = useDuplicar(predefinicao.id);
  const [nome, setNome] = useState(`Cópia de ${predefinicao.nome}`.slice(0, 120));
  return (
    <Modal opened onClose={onFechar} title={`Duplicar «${predefinicao.nome}»`} centered>
      <Stack>
        <TextInput label="Nome da cópia" value={nome} maxLength={120} onChange={(e) => setNome(e.currentTarget.value)} />
        {duplicar.error && (
          <Alert color="red" role="alert">
            {mensagemComCampos(duplicar.error, { rotulos: { nome: "Nome da cópia" } })}
          </Alert>
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onFechar}>
            Cancelar
          </Button>
          <Button
            disabled={!nome.trim()}
            loading={duplicar.isPending}
            onClick={() => duplicar.mutate(nome.trim(), { onSuccess: onFechar })}
          >
            Duplicar
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function TelaPredefinicoes() {
  const predefinicoes = usePredefinicoes();
  const projetos = useProjetos();
  const rotulos = useRotulos();
  const tipos = useTipos();
  const contas = useContas();
  const [criandoPadrao, setCriandoPadrao] = useState(false);
  const [editando, setEditando] = useState<Predefinicao | null>(null);
  const [duplicando, setDuplicando] = useState<Predefinicao | null>(null);

  const erro = predefinicoes.error ?? projetos.error ?? rotulos.error ?? tipos.error ?? contas.error;
  const usos = (id: string) => (projetos.data ?? []).filter((p) => p.predefinicao === id).length;
  const pronto = rotulos.data && tipos.data && contas.data && projetos.data;

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={1} size="h2">
          Predefinições de fluxo
        </Title>
        <Button onClick={() => setCriandoPadrao(true)}>Criar a partir do Padrão</Button>
      </Group>
      {erro && (
        <Alert color="red" role="alert">
          {erro.message}
        </Alert>
      )}
      {predefinicoes.isPending && !erro && <Loader aria-label="Carregando predefinições" />}
      {predefinicoes.data?.length === 0 && (
        <Text c="dimmed">Nenhuma predefinição ainda. Clique em «Criar a partir do Padrão» para começar.</Text>
      )}
      {predefinicoes.data?.map((p) => {
        const n = usos(p.id);
        return (
          <Paper withBorder p="md" key={p.id} data-predefinicao={p.id}>
            <Group justify="space-between" wrap="wrap">
              <Stack gap={2}>
                <Text fw={600}>{p.nome}</Text>
                {p.descricao && (
                  <Text size="sm" c="dimmed">
                    {p.descricao}
                  </Text>
                )}
                <Text size="sm">{n === 1 ? "Usada por 1 projeto" : `Usada por ${n} projetos`}</Text>
              </Stack>
              <Group>
                <Button variant="default" disabled={!pronto} onClick={() => setEditando(p)}>
                  Editar
                </Button>
                <Button variant="default" onClick={() => setDuplicando(p)}>
                  Duplicar
                </Button>
              </Group>
            </Group>
          </Paper>
        );
      })}
      {criandoPadrao && <CriarPadrao onFechar={() => setCriandoPadrao(false)} />}
      {duplicando && <Duplicar predefinicao={duplicando} onFechar={() => setDuplicando(null)} />}
      {editando && rotulos.data && tipos.data && contas.data && (
        <EditorPredefinicao
          predefinicao={editando}
          usos={usos(editando.id)}
          rotulos={rotulos.data}
          tipos={tipos.data}
          contas={contas.data}
          onFechar={() => setEditando(null)}
        />
      )}
    </Stack>
  );
}
