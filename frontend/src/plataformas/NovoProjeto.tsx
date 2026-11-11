import { Alert, Button, Group, Modal, NativeSelect, Stack, Text, TextInput } from "@mantine/core";
import { useState } from "react";
import { camposDoErro } from "../api/campos";
import { useClientes } from "../contas/api";
import { Conferencia } from "./Conferencia";
import { type Conexao, type Projeto, itensDoProjeto, useCriarProjeto, usePredefinicoes, useRepositorios } from "./api";

type Props = { conexoes: Conexao[]; onFechar: () => void };

export function NovoProjeto({ conexoes, onFechar }: Props) {
  const [conexao, setConexao] = useState("");
  const [busca, setBusca] = useState("");
  const [repositorio, setRepositorio] = useState("");
  const [nome, setNome] = useState("");
  const [cliente, setCliente] = useState("");
  const [predefinicao, setPredefinicao] = useState("");
  const [criado, setCriado] = useState<Projeto | null>(null);

  const repositorios = useRepositorios(conexao);
  const clientes = useClientes();
  const predefinicoes = usePredefinicoes();
  const criar = useCriarProjeto();

  const filtrados = (repositorios.data ?? []).filter((r) =>
    r.caminho.toLowerCase().includes(busca.trim().toLowerCase()),
  );

  function escolherRepositorio(id: string) {
    setRepositorio(id);
    const caminho = repositorios.data?.find((r) => r.id_externo === id)?.caminho ?? "";
    setNome(caminho.split("/").pop() ?? "");
  }

  function enviar() {
    criar.mutate(
      {
        nome: nome.trim(),
        conexao,
        repositorio_id_externo: repositorio,
        cliente: cliente || null,
        predefinicao: predefinicao || null,
      },
      { onSuccess: setCriado },
    );
  }

  const erroDeCampos = camposDoErro(criar.error);
  const doCampo = (chave: string) => erroDeCampos[chave]?.join(" ");

  if (criado) {
    return (
      <Modal opened onClose={onFechar} title={`Projeto «${criado.nome}» criado`} size="lg" centered>
        <Stack>
          <Text size="sm">Conferência do repositório:</Text>
          <Conferencia
            projetoId={criado.id}
            itens={itensDoProjeto(criado)}
            erroAoPreparar={criado.erro_ao_preparar}
          />
          <Group justify="flex-end">
            <Button onClick={onFechar}>Fechar</Button>
          </Group>
        </Stack>
      </Modal>
    );
  }

  return (
    <Modal opened onClose={onFechar} title="Novo projeto" size="lg" centered>
      <Stack>
        <NativeSelect
          label="Conexão"
          value={conexao}
          error={doCampo("conexao")}
          onChange={(e) => {
            setConexao(e.currentTarget.value);
            setRepositorio("");
            setNome("");
            setBusca("");
          }}
          data={[{ value: "", label: "Escolha uma conexão" }, ...conexoes.map((c) => ({ value: c.id, label: c.nome }))]}
        />
        {conexao && (
          <>
            <TextInput
              label="Buscar repositório"
              value={busca}
              onChange={(e) => setBusca(e.currentTarget.value)}
              disabled={repositorios.isPending}
            />
            {repositorios.error && (
              <Alert color="red" role="alert">
                {repositorios.error.message}
              </Alert>
            )}
            <NativeSelect
              label="Repositório"
              value={repositorio}
              disabled={repositorios.isPending}
              error={doCampo("repositorio_id_externo")}
              onChange={(e) => escolherRepositorio(e.currentTarget.value)}
              data={[
                { value: "", label: repositorios.isPending ? "Carregando…" : "Escolha um repositório" },
                ...filtrados.map((r) => ({ value: r.id_externo, label: r.caminho })),
              ]}
            />
          </>
        )}
        <TextInput
          label="Nome do projeto"
          required
          value={nome}
          error={doCampo("nome")}
          onChange={(e) => setNome(e.currentTarget.value)}
        />
        <NativeSelect
          label="Cliente (opcional)"
          value={cliente}
          error={doCampo("cliente")}
          onChange={(e) => setCliente(e.currentTarget.value)}
          data={[{ value: "", label: "Sem cliente" }, ...(clientes.data ?? []).map((c) => ({ value: c.id, label: c.nome }))]}
        />
        <NativeSelect
          label="Predefinição (opcional)"
          value={predefinicao}
          error={doCampo("predefinicao")}
          onChange={(e) => setPredefinicao(e.currentTarget.value)}
          data={[
            { value: "", label: "Sem predefinição" },
            ...(predefinicoes.data ?? []).map((p) => ({ value: p.id, label: p.nome })),
          ]}
        />
        {criar.error && (
          <Alert color="red" role="alert">
            {criar.error.message}
          </Alert>
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onFechar}>
            Cancelar
          </Button>
          <Button
            loading={criar.isPending}
            disabled={!conexao || !repositorio || nome.trim() === ""}
            onClick={enviar}
          >
            Criar projeto
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
