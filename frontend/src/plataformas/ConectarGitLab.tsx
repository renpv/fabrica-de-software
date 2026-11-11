import { Alert, Anchor, Button, Group, List, Modal, PasswordInput, Stack, TextInput } from "@mantine/core";
import { useState } from "react";
import { ErroDeApi } from "../api/chamar";
import { useCriarGitLab } from "./api";

export function ConectarGitLab({ onFechar }: { onFechar: () => void }) {
  const [nome, setNome] = useState("");
  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const criar = useCriarGitLab();

  const erro = criar.error;
  const campos = erro instanceof ErroDeApi ? erro.campos : {};
  const doCampo = (chave: string) => campos[chave]?.join(" ");
  const semCampo = Object.entries(campos)
    .filter(([c]) => !["nome", "url_base", "token"].includes(c))
    .flatMap(([, v]) => v);

  function enviar(e: React.FormEvent) {
    e.preventDefault();
    // Em caso de erro o formulário fica como está: nada é apagado.
    criar.mutate({ nome: nome.trim(), url_base: url.trim(), token }, { onSuccess: onFechar });
  }

  return (
    <Modal opened onClose={onFechar} title="Conectar GitLab" size="lg" centered>
      <form onSubmit={enviar}>
        <Stack>
          <List type="ordered" spacing="xs" size="sm">
            <List.Item>
              No GitLab, abra <strong>Preferências, Tokens de acesso</strong> (na instância, em{" "}
              <Anchor href="https://docs.gitlab.com/user/profile/personal_access_tokens/" target="_blank" rel="noreferrer noopener">
                como criar um token
              </Anchor>
              ).
            </List.Item>
            <List.Item>
              Marque o escopo <strong>api</strong> e crie o token.
            </List.Item>
            <List.Item>
              A conta dona do token precisa do papel <strong>Maintainer</strong> nos projetos que a central vai usar.
            </List.Item>
            <List.Item>Cole o token abaixo. Ele fica guardado cifrado e nunca é mostrado de volta.</List.Item>
          </List>
          <TextInput
            label="Nome da conexão"
            required
            value={nome}
            error={doCampo("nome")}
            onChange={(e) => setNome(e.currentTarget.value)}
          />
          <TextInput
            label="URL da instância"
            description="Por exemplo, https://gitlab.com ou o endereço do GitLab da sua empresa."
            required
            value={url}
            error={doCampo("url_base")}
            onChange={(e) => setUrl(e.currentTarget.value)}
          />
          <PasswordInput
            label="Token de acesso"
            required
            autoComplete="off"
            value={token}
            error={doCampo("token")}
            onChange={(e) => setToken(e.currentTarget.value)}
          />
          {erro && (
            <Alert color="red" role="alert">
              {erro.message}
              {semCampo.map((m) => ` ${m}`)}
            </Alert>
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={onFechar}>
              Cancelar
            </Button>
            <Button
              type="submit"
              loading={criar.isPending}
              disabled={nome.trim() === "" || url.trim() === "" || token === ""}
            >
              Conectar
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
