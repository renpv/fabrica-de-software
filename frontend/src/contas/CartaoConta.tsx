import { Alert, Badge, Button, Group, Modal, Paper, Stack, Text } from "@mantine/core";
import { useState } from "react";
import { type Conta, useExcluirConta, useTestarConta } from "./api";

const SELOS: Record<Conta["status"], { rotulo: string; cor: string }> = {
  ok: { rotulo: "ok", cor: "green" },
  falha: { rotulo: "falha", cor: "red" },
  aguardando_runner: { rotulo: "aguardando runner", cor: "yellow" },
  nao_testada: { rotulo: "não testada", cor: "gray" },
};

type Props = {
  conta: Conta;
  nomeDoTipo: string;
  nomeDoCliente: string | null;
  onEditar: (conta: Conta) => void;
};

export function CartaoConta({ conta, nomeDoTipo, nomeDoCliente, onEditar }: Props) {
  const testar = useTestarConta();
  const excluir = useExcluirConta();
  const [confirmando, setConfirmando] = useState(false);
  const selo = SELOS[conta.status];
  const erro = testar.error?.message ?? excluir.error?.message ?? null;

  return (
    <Paper withBorder p="md" data-conta={conta.id}>
      <Stack gap="xs">
        <Group justify="space-between" wrap="wrap">
          <Text fw={600}>{conta.nome}</Text>
          <Badge color={selo.cor}>{selo.rotulo}</Badge>
        </Group>
        <Group gap="xs">
          <Text size="sm" c="dimmed">
            {nomeDoTipo}
          </Text>
          <Text size="sm" c="dimmed" aria-hidden>
            ·
          </Text>
          <Text size="sm" c="dimmed">
            {nomeDoCliente ?? "Sua"}
          </Text>
        </Group>
        {conta.ultimo_teste_mensagem && <Text size="sm">{conta.ultimo_teste_mensagem}</Text>}
        {erro && (
          <Alert color="red" role="alert">
            {erro}
          </Alert>
        )}
        <Group gap="xs">
          <Button variant="default" size="xs" loading={testar.isPending} onClick={() => testar.mutate(conta.id)}>
            Testar de novo
          </Button>
          <Button variant="default" size="xs" onClick={() => onEditar(conta)}>
            Editar
          </Button>
          <Button variant="light" color="red" size="xs" onClick={() => setConfirmando(true)}>
            Excluir
          </Button>
        </Group>
      </Stack>
      <Modal opened={confirmando} onClose={() => setConfirmando(false)} title="Excluir conta" centered>
        <Stack>
          <Text>Excluir a conta «{conta.nome}»? Esta ação não pode ser desfeita.</Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setConfirmando(false)}>
              Cancelar
            </Button>
            <Button
              color="red"
              loading={excluir.isPending}
              onClick={() => excluir.mutate(conta.id, { onSuccess: () => setConfirmando(false) })}
            >
              Confirmar exclusão
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Paper>
  );
}
