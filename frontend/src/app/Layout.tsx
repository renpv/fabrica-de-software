import { Alert, AppShell, Burger, Button, Group, NavLink, Text } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { NavLink as LinkDaRota, Outlet } from "react-router";
import { useSessao } from "../sessao/useSessao";

const itens = [
  { rotulo: "Contas de agente", para: "/contas" },
  { rotulo: "Plataformas e projetos", para: "/plataformas" },
  { rotulo: "Predefinições", para: "/predefinicoes" },
];

export function Layout() {
  const { sessao, sair, erroAoSair } = useSessao();
  const [aberto, { toggle, close }] = useDisclosure(false);

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 260, breakpoint: "sm", collapsed: { mobile: !aberto } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Burger opened={aberto} onClick={toggle} hiddenFrom="sm" size="sm" aria-label="Abrir ou fechar o menu" />
            <Text fw={600}>Fábrica de software</Text>
          </Group>
          <Group>
            <Text size="sm">{sessao?.dono.nome}</Text>
            <Button variant="default" size="xs" onClick={() => sair()}>
              Sair
            </Button>
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="md" component="nav" aria-label="Navegação principal">
        {itens.map((item) => (
          <NavLink key={item.para} component={LinkDaRota} to={item.para} label={item.rotulo} onClick={close} />
        ))}
      </AppShell.Navbar>
      <AppShell.Main>
        {erroAoSair && (
          <Alert color="red" role="alert" mb="md">
            {erroAoSair}
          </Alert>
        )}
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
