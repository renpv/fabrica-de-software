import { Stack, Text, Title } from "@mantine/core";

/** Tela provisória: as Tasks 12 a 14 preenchem cada uma. */
export function Pagina({ titulo }: { titulo: string }) {
  return (
    <Stack>
      <Title order={1} size="h2">
        {titulo}
      </Title>
      <Text c="dimmed">Esta tela ainda está em construção.</Text>
    </Stack>
  );
}
