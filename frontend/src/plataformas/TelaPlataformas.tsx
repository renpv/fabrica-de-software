import { Alert, Anchor, Badge, Button, Group, Loader, Modal, Paper, Stack, Text, Title } from "@mantine/core";
import { useState } from "react";
import { useSearchParams } from "react-router";
import { Conferencia } from "./Conferencia";
import { ConectarGitHub } from "./ConectarGitHub";
import { ConectarGitLab } from "./ConectarGitLab";
import { NovoProjeto } from "./NovoProjeto";
import {
  type Conexao,
  type Projeto,
  itensDoProjeto,
  mensagemDoCodigo,
  useConexoes,
  useExcluirConexao,
  useExcluirProjeto,
  useProjetos,
} from "./api";

// O back-end não expõe o slug do App (fica nas credenciais cifradas); a lista de Apps do usuário serve.
const URL_APPS_GITHUB = "https://github.com/settings/apps";

const SELOS: Record<Conexao["status"], { rotulo: string; cor: string }> = {
  ok: { rotulo: "funcionando", cor: "green" },
  falha: { rotulo: "com falha", cor: "red" },
  nao_testada: { rotulo: "não testada", cor: "gray" },
};

function faltaInstalar(conexao: Conexao): boolean {
  const config = (conexao.config ?? {}) as { installation_id?: unknown };
  return conexao.tipo === "github" && !config.installation_id;
}

function CartaoConexao({ conexao }: { conexao: Conexao }) {
  const excluir = useExcluirConexao();
  const [confirmando, setConfirmando] = useState(false);
  const selo = SELOS[conexao.status];

  return (
    <Paper withBorder p="md" data-conexao={conexao.id}>
      <Stack gap="xs">
        <Group justify="space-between" wrap="wrap">
          <Text fw={600}>{conexao.nome}</Text>
          <Badge color={selo.cor}>{selo.rotulo}</Badge>
        </Group>
        <Text size="sm" c="dimmed">
          {conexao.tipo === "github" ? "GitHub" : `GitLab · ${conexao.url_base}`}
        </Text>
        {conexao.ultimo_teste_mensagem && <Text size="sm">{conexao.ultimo_teste_mensagem}</Text>}
        {faltaInstalar(conexao) && (
          <Alert color="yellow" title="Falta instalar o App">
            <Stack gap="xs" align="flex-start">
              <Text size="sm">
                O App foi criado, mas ainda não foi instalado em nenhum repositório. Abra o App no GitHub e clique em
                «Install».
              </Text>
              <Button
                component="a"
                href={URL_APPS_GITHUB}
                target="_blank"
                rel="noreferrer noopener"
                size="xs"
              >
                Instalar no GitHub
              </Button>
            </Stack>
          </Alert>
        )}
        {excluir.error && !confirmando && (
          <Alert color="red" role="alert">
            {excluir.error.message}
          </Alert>
        )}
        <Group gap="xs">
          <Button variant="light" color="red" size="xs" onClick={() => setConfirmando(true)}>
            Excluir
          </Button>
        </Group>
      </Stack>
      <Modal
        opened={confirmando}
        onClose={() => {
          setConfirmando(false);
          excluir.reset();
        }}
        title="Excluir conexão"
        centered
      >
        <Stack>
          <Text>Excluir a conexão «{conexao.nome}»? Esta ação não pode ser desfeita.</Text>
          {conexao.tipo === "github" && (
            <Alert color="yellow">
              Excluir aqui <strong>não remove o App no GitHub</strong>. Para apagá-lo, abra{" "}
              <Anchor href={URL_APPS_GITHUB} target="_blank" rel="noreferrer noopener">
                {URL_APPS_GITHUB}
              </Anchor>
              , escolha o App «Fabrica {conexao.nome}» e remova-o.
            </Alert>
          )}
          {excluir.error && (
            <Alert color="red" role="alert">
              {excluir.error.message}
            </Alert>
          )}
          <Group justify="flex-end">
            <Button
              variant="default"
              onClick={() => {
                setConfirmando(false);
                excluir.reset();
              }}
            >
              Cancelar
            </Button>
            <Button
              color="red"
              loading={excluir.isPending}
              onClick={() => excluir.mutate(conexao.id, { onSuccess: () => setConfirmando(false) })}
            >
              Confirmar exclusão
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Paper>
  );
}

function CartaoProjeto({ projeto, nomeDaConexao }: { projeto: Projeto; nomeDaConexao: string }) {
  const excluir = useExcluirProjeto();
  const [confirmando, setConfirmando] = useState(false);

  return (
    <Paper withBorder p="md" data-projeto={projeto.id}>
      <Stack gap="xs">
        <Group justify="space-between" wrap="wrap">
          <Text fw={600}>{projeto.nome}</Text>
          <Anchor href={projeto.repositorio_url} target="_blank" rel="noreferrer noopener" size="sm">
            {projeto.repositorio_caminho}
          </Anchor>
        </Group>
        <Text size="sm" c="dimmed">
          {nomeDaConexao}
        </Text>
        <Conferencia
          projetoId={projeto.id}
          itens={itensDoProjeto(projeto)}
          erroAoPreparar={projeto.erro_ao_preparar}
        />
        {excluir.error && !confirmando && (
          <Alert color="red" role="alert">
            {excluir.error.message}
          </Alert>
        )}
        <Group gap="xs">
          <Button variant="light" color="red" size="xs" onClick={() => setConfirmando(true)}>
            Excluir projeto
          </Button>
        </Group>
      </Stack>
      <Modal opened={confirmando} onClose={() => setConfirmando(false)} title="Excluir projeto" centered>
        <Stack>
          <Text>Excluir o projeto «{projeto.nome}»? O repositório não é apagado.</Text>
          {excluir.error && (
            <Alert color="red" role="alert">
              {excluir.error.message}
            </Alert>
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setConfirmando(false)}>
              Cancelar
            </Button>
            <Button
              color="red"
              loading={excluir.isPending}
              onClick={() => excluir.mutate(projeto.id, { onSuccess: () => setConfirmando(false) })}
            >
              Confirmar exclusão
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Paper>
  );
}

export function TelaPlataformas() {
  const conexoes = useConexoes();
  const projetos = useProjetos();
  const [params, setParams] = useSearchParams();
  const [dialogo, setDialogo] = useState<"github" | "gitlab" | "projeto" | null>(null);

  const codigoDeErro = params.get("erro");
  const erro = conexoes.error ?? projetos.error;
  const nomeDaConexao = (id: string) => conexoes.data?.find((c) => c.id === id)?.nome ?? "";

  function dispensarErro() {
    const proximos = new URLSearchParams(params);
    proximos.delete("erro");
    setParams(proximos, { replace: true });
  }

  return (
    <Stack>
      <Title order={1} size="h2">
        Plataformas e projetos
      </Title>
      {codigoDeErro !== null && (
        <Alert color="red" role="alert" withCloseButton closeButtonLabel="Dispensar" onClose={dispensarErro}>
          {mensagemDoCodigo(codigoDeErro)}
        </Alert>
      )}
      {erro && (
        <Alert color="red" role="alert">
          {erro.message}
        </Alert>
      )}

      <Group justify="space-between">
        <Title order={2} size="h3">
          Conexões
        </Title>
        <Group gap="xs">
          <Button onClick={() => setDialogo("github")}>Conectar GitHub</Button>
          <Button onClick={() => setDialogo("gitlab")}>Conectar GitLab</Button>
        </Group>
      </Group>
      {conexoes.isPending && !erro && <Loader aria-label="Carregando conexões" />}
      {conexoes.data?.length === 0 && (
        <Text c="dimmed">Nenhuma conexão ainda. Conecte o GitHub ou o GitLab para criar projetos.</Text>
      )}
      {conexoes.data?.map((c) => <CartaoConexao key={c.id} conexao={c} />)}

      <Group justify="space-between">
        <Title order={2} size="h3">
          Projetos
        </Title>
        <Button onClick={() => setDialogo("projeto")} disabled={!conexoes.data?.length}>
          Novo projeto
        </Button>
      </Group>
      {projetos.data?.length === 0 && (
        <Text c="dimmed">Nenhum projeto ainda. Depois de conectar uma plataforma, clique em «Novo projeto».</Text>
      )}
      {projetos.data?.map((p) => (
        <CartaoProjeto key={p.id} projeto={p} nomeDaConexao={nomeDaConexao(p.conexao)} />
      ))}

      {dialogo === "github" && <ConectarGitHub onFechar={() => setDialogo(null)} />}
      {dialogo === "gitlab" && <ConectarGitLab onFechar={() => setDialogo(null)} />}
      {dialogo === "projeto" && conexoes.data && (
        <NovoProjeto conexoes={conexoes.data} onFechar={() => setDialogo(null)} />
      )}
    </Stack>
  );
}
