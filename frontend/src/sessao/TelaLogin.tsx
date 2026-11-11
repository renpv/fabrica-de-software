import { Alert, Button, Center, Paper, PasswordInput, Stack, TextInput, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { Navigate } from "react-router";
import { useSessao } from "./useSessao";

export function TelaLogin() {
  const { sessao, erroDeLogin, entrando, entrar } = useSessao();
  const form = useForm({ initialValues: { usuario: "", senha: "" } });

  if (sessao) return <Navigate to="/contas" replace />;

  return (
    <Center mih="100vh" p="md">
      <Paper withBorder shadow="sm" p="xl" w={380} maw="100%">
        <form onSubmit={form.onSubmit(({ usuario, senha }) => entrar(usuario, senha))}>
          <Stack>
            <Title order={1} size="h2">
              Entrar na fábrica
            </Title>
            {erroDeLogin && (
              <Alert color="red" role="alert">
                {erroDeLogin}
              </Alert>
            )}
            <TextInput label="Usuário" autoComplete="username" required {...form.getInputProps("usuario")} />
            <PasswordInput label="Senha" autoComplete="current-password" required {...form.getInputProps("senha")} />
            <Button type="submit" loading={entrando}>
              Entrar
            </Button>
          </Stack>
        </form>
      </Paper>
    </Center>
  );
}
