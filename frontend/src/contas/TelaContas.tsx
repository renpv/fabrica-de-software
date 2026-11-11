import { Alert, Button, Group, Loader, Stack, Text, Title } from "@mantine/core";
import { useState } from "react";
import { AssistenteConta } from "./AssistenteConta";
import { CartaoConta } from "./CartaoConta";
import { type Conta, useClientes, useContas, useTipos } from "./api";

export function TelaContas() {
  const contas = useContas();
  const tipos = useTipos();
  const clientes = useClientes();
  const [assistente, setAssistente] = useState<{ conta?: Conta } | null>(null);

  const erro = contas.error ?? tipos.error ?? clientes.error;
  const nomeDoTipo = (tipo: string) => tipos.data?.find((t) => t.tipo === tipo)?.nome ?? tipo;
  const nomeDoCliente = (id?: string | null) =>
    id ? (clientes.data?.find((c) => c.id === id)?.nome ?? null) : null;

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={1} size="h2">
          Contas de agente
        </Title>
        <Button onClick={() => setAssistente({})} disabled={!tipos.data}>
          Nova conta
        </Button>
      </Group>
      {erro && (
        <Alert color="red" role="alert">
          {erro.message}
        </Alert>
      )}
      {contas.isPending && !erro && <Loader aria-label="Carregando contas" />}
      {contas.data?.length === 0 && (
        <Text c="dimmed">Nenhuma conta ainda. Clique em «Nova conta» para conectar um agente.</Text>
      )}
      {contas.data?.map((conta) => (
        <CartaoConta
          key={conta.id}
          conta={conta}
          nomeDoTipo={nomeDoTipo(conta.tipo)}
          nomeDoCliente={nomeDoCliente(conta.cliente)}
          onEditar={(c) => setAssistente({ conta: c })}
        />
      ))}
      {assistente && tipos.data && (
        <AssistenteConta
          tipos={tipos.data}
          clientes={clientes.data ?? []}
          conta={assistente.conta}
          onFechar={() => setAssistente(null)}
        />
      )}
    </Stack>
  );
}
