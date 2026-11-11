import { Button, Group, Modal, Stack, Text, TextInput } from "@mantine/core";
import { camposDoErro } from "../api/campos";
import { useEffect, useRef, useState } from "react";
import { useManifesto } from "./api";

/**
 * O GitHub só aceita o manifesto por POST de formulário. A central pede o manifesto ao
 * back-end e envia um `<form method="post">` com o JSON no campo oculto `manifest`.
 */
export function ConectarGitHub({ onFechar }: { onFechar: () => void }) {
  const [nome, setNome] = useState("");
  const manifesto = useManifesto();
  const formulario = useRef<HTMLFormElement>(null);
  const resposta = manifesto.data;

  useEffect(() => {
    if (resposta) formulario.current?.requestSubmit();
  }, [resposta]);

  const campos = camposDoErro(manifesto.error);

  return (
    <Modal opened onClose={onFechar} title="Conectar GitHub" centered>
      <Stack>
        <Text size="sm">
          A central cria um App no GitHub só para ela. Você escolhe o nome, confirma no GitHub e depois instala o
          App nos repositórios que quiser usar.
        </Text>
        <TextInput
          label="Nome da conexão"
          description="Aparece no GitHub como «Fabrica <nome>». Até 26 caracteres."
          required
          maxLength={26}
          value={nome}
          error={campos.nome?.join(" ")}
          onChange={(e) => setNome(e.currentTarget.value)}
        />
        {manifesto.error && !campos.nome && (
          <Text c="red" size="sm" role="alert">
            {manifesto.error.message}
          </Text>
        )}
        {resposta && (
          <form ref={formulario} method="post" action={resposta.acao}>
            <input type="hidden" name="manifest" value={JSON.stringify(resposta.manifesto)} />
            <Text size="sm" mb="xs">
              Levando você ao GitHub. Se nada acontecer, use o botão abaixo.
            </Text>
            <Button type="submit" variant="default">
              Ir para o GitHub
            </Button>
          </form>
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onFechar}>
            Cancelar
          </Button>
          <Button
            loading={manifesto.isPending}
            disabled={nome.trim() === "" || Boolean(resposta)}
            onClick={() => manifesto.mutate(nome.trim())}
          >
            Criar App no GitHub
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
