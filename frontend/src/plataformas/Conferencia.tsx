import { Alert, Button, Group, List, Stack, Text } from "@mantine/core";
import { type ItemConferencia, useConferencia } from "./api";

type Props = {
  projetoId: string;
  /** Última conferência gravada no projeto. */
  itens: ItemConferencia[];
  erroAoPreparar?: string;
};

/** Um item por linha, com ✓ ou ✗. "Conferir" só olha; "Consertar" cria o que falta. */
export function Conferencia({ projetoId, itens, erroAoPreparar }: Props) {
  const conferir = useConferencia(projetoId, "conferir");
  const consertar = useConferencia(projetoId, "preparar");
  const atual = consertar.data?.itens ?? conferir.data?.itens ?? itens;
  const erro = conferir.error?.message ?? consertar.error?.message ?? null;
  const podeConsertar = atual.some((i) => !i.ok && i.consertavel);

  return (
    <Stack gap="xs">
      {erroAoPreparar && (
        <Alert color="red" role="alert">
          {erroAoPreparar}
        </Alert>
      )}
      {atual.length === 0 ? (
        <Text size="sm" c="dimmed">
          Ainda não conferido. Clique em «Conferir».
        </Text>
      ) : (
        <List listStyleType="none" spacing={4}>
          {atual.map((i) => (
            <List.Item key={i.chave}>
              <Group gap="xs" wrap="nowrap" align="flex-start">
                <Text c={i.ok ? "green" : "red"} fw={700} aria-label={i.ok ? "ok" : "falhou"}>
                  {i.ok ? "✓" : "✗"}
                </Text>
                <div>
                  <Text size="sm" fw={500}>
                    {i.titulo}
                  </Text>
                  <Text size="sm" c="dimmed">
                    {i.mensagem}
                  </Text>
                </div>
              </Group>
            </List.Item>
          ))}
        </List>
      )}
      {erro && (
        <Alert color="red" role="alert">
          {erro}
        </Alert>
      )}
      <Group gap="xs">
        <Button
          variant="default"
          size="xs"
          loading={conferir.isPending}
          disabled={consertar.isPending}
          onClick={() => conferir.mutate()}
        >
          Conferir
        </Button>
        {podeConsertar && (
          <Button size="xs" loading={consertar.isPending} disabled={conferir.isPending} onClick={() => consertar.mutate()}>
            Consertar
          </Button>
        )}
      </Group>
    </Stack>
  );
}
