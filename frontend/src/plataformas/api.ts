import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { chamar } from "../api/chamar";
import { api } from "../api/cliente";
import type { components } from "../api/schema";

export type Conexao = components["schemas"]["ConexaoPlataforma"];
export type Projeto = components["schemas"]["Projeto"];
export type Predefinicao = components["schemas"]["Predefinicao"];
export type Repositorio = components["schemas"]["Repositorio"];
export type ItemConferencia = components["schemas"]["ItemConferencia"];
export type Manifesto = components["schemas"]["ManifestoResposta"];

/** Mensagens dos códigos de `?erro=` (cópia de `backend/apps/plataformas/erros.py`). */
export const MENSAGENS_DE_ERRO: Record<string, string> = {
  sem_login: "Sua sessão expirou. Entre de novo e conecte o GitHub outra vez.",
  estado_invalido:
    "O link de conexão com o GitHub é inválido, expirou ou já foi usado. Comece de novo pela tela de plataformas.",
  conversao_falhou:
    "O GitHub não aceitou criar o App (o código vale 1 hora e uma vez só). Comece de novo e crie o App outra vez.",
  conversao_sem_registro:
    "O App foi criado no GitHub, mas a central não conseguiu salvar a conexão. Apague o App em https://github.com/settings/apps e comece de novo.",
  instalacao_invalida:
    "Essa instalação não pertence ao App desta conexão. Instale o App criado pela central e tente de novo.",
  github_fora_do_ar:
    "Não consegui falar com o GitHub agora, ou ele limitou as chamadas. Tente de novo em alguns minutos.",
};

export const MENSAGEM_ERRO_GENERICA =
  "Algo deu errado ao conectar o GitHub. Comece de novo pela tela de plataformas.";

/** Texto em pt-BR para o código de `?erro=`; o valor da URL nunca vai para a tela. */
export function mensagemDoCodigo(codigo: string): string {
  return Object.hasOwn(MENSAGENS_DE_ERRO, codigo) ? MENSAGENS_DE_ERRO[codigo] : MENSAGEM_ERRO_GENERICA;
}

export function useConexoes() {
  const qc = useQueryClient();
  return useQuery({
    queryKey: ["conexoes-plataforma"],
    queryFn: () => chamar(qc, () => api.GET("/api/conexoes-plataforma/")),
  });
}

export function useProjetos() {
  const qc = useQueryClient();
  return useQuery({
    queryKey: ["projetos"],
    queryFn: () => chamar(qc, () => api.GET("/api/projetos/")),
  });
}

export function usePredefinicoes() {
  const qc = useQueryClient();
  return useQuery({
    queryKey: ["predefinicoes"],
    queryFn: () => chamar(qc, () => api.GET("/api/predefinicoes/")),
  });
}

export function useRepositorios(conexaoId: string) {
  const qc = useQueryClient();
  return useQuery({
    queryKey: ["repositorios", conexaoId],
    enabled: conexaoId !== "",
    queryFn: () =>
      chamar(qc, () =>
        api.GET("/api/conexoes-plataforma/{id}/repositorios/", { params: { path: { id: conexaoId } } }),
      ),
  });
}

export function useManifesto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (nome: string) =>
      chamar(qc, () => api.POST("/api/conexoes-plataforma/github/manifesto/", { body: { nome } })),
  });
}

export function useCriarGitLab() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: { nome: string; url_base: string; token: string }) =>
      chamar(qc, () => api.POST("/api/conexoes-plataforma/gitlab/", { body: dados })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conexoes-plataforma"] }),
  });
}

export function useExcluirConexao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      chamar(qc, () => api.DELETE("/api/conexoes-plataforma/{id}/", { params: { path: { id } } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conexoes-plataforma"] }),
  });
}

export type DadosDoProjeto = {
  nome: string;
  conexao: string;
  repositorio_id_externo: string;
  cliente: string | null;
  predefinicao: string | null;
};

export function useCriarProjeto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: DadosDoProjeto) => chamar(qc, () => api.POST("/api/projetos/", { body: dados })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projetos"] }),
  });
}

export function useExcluirProjeto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      chamar(qc, () => api.DELETE("/api/projetos/{id}/", { params: { path: { id } } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projetos"] }),
  });
}

/** `conferir` só olha; `preparar` cria o que falta. As duas devolvem a conferência nova. */
export function useConferencia(id: string, acao: "conferir" | "preparar") {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      acao === "conferir"
        ? chamar(qc, () => api.POST("/api/projetos/{id}/conferir/", { params: { path: { id } } }))
        : chamar(qc, () => api.POST("/api/projetos/{id}/preparar/", { params: { path: { id } } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projetos"] }),
  });
}

/** `conferencia` vem como JSON livre; só aceita a lista de itens. */
export function itensDoProjeto(projeto: Projeto): ItemConferencia[] {
  return Array.isArray(projeto.conferencia) ? (projeto.conferencia as ItemConferencia[]) : [];
}
