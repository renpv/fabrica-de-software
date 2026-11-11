import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, mensagemDeErro } from "../api/cliente";

// O openapi.yaml não descreve o corpo da sessão, então o tipo é escrito à mão.
export type Sessao = { usuario: string; dono: { id: string; nome: string } };

const CHAVE = ["sessao"] as const;
const MENSAGEM_PADRAO = "Não foi possível falar com o servidor. Verifique a conexão e tente de novo.";

export class ErroDeSessao extends Error {}

async function buscarSessao(): Promise<Sessao | null> {
  const { data, response } = await api.GET("/api/sessao/");
  if (response.status === 401 || response.status === 403) return null;
  if (!response.ok) throw new ErroDeSessao(MENSAGEM_PADRAO);
  return data as unknown as Sessao;
}

export function useSessao() {
  const queryClient = useQueryClient();
  const consulta = useQuery({ queryKey: CHAVE, queryFn: buscarSessao });

  const entrarMutacao = useMutation({
    mutationFn: async ({ usuario, senha }: { usuario: string; senha: string }) => {
      const { data, error, response } = await api.POST("/api/sessao/", {
        body: { usuario, senha },
      });
      if (!response.ok) throw new ErroDeSessao(mensagemDeErro(error, MENSAGEM_PADRAO));
      return data as unknown as Sessao;
    },
    onSuccess: (sessao) => queryClient.setQueryData(CHAVE, sessao),
  });

  const sairMutacao = useMutation({
    mutationFn: async () => {
      await api.DELETE("/api/sessao/");
    },
    onSettled: () => queryClient.setQueryData(CHAVE, null),
  });

  return {
    /** `undefined` enquanto carrega, `null` sem sessão. */
    sessao: consulta.data,
    carregando: consulta.isPending,
    erroDeLogin: entrarMutacao.error ? entrarMutacao.error.message : null,
    entrando: entrarMutacao.isPending,
    entrar: (usuario: string, senha: string) => entrarMutacao.mutateAsync({ usuario, senha }).catch(() => undefined),
    sair: () => sairMutacao.mutateAsync(),
  };
}
