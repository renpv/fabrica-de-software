import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { api, mensagemDeErro } from "../api/cliente";
import type { components } from "../api/schema";

export type Conta = components["schemas"]["ContaAgente"];
export type TipoDeAgente = components["schemas"]["TipoDeAgente"];
export type Cliente = components["schemas"]["Cliente"];
export type ResultadoTeste = components["schemas"]["ResultadoTeste"];

export const MENSAGEM_REDE = "Não foi possível falar com o servidor. Verifique a conexão e tente de novo.";

/** Erro de uma chamada, já com texto em pt-BR; `campos` traz os erros por campo de um 400. */
export class ErroDeApi extends Error {
  campos: Record<string, string[]>;
  constructor(mensagem: string, campos: Record<string, string[]> = {}) {
    super(mensagem);
    this.campos = campos;
  }
}

function errosPorCampo(erro: unknown): Record<string, string[]> {
  const campos: Record<string, string[]> = {};
  if (erro && typeof erro === "object" && !Array.isArray(erro)) {
    for (const [campo, valor] of Object.entries(erro)) {
      if (campo === "detail") continue;
      if (Array.isArray(valor)) campos[campo] = valor.filter((v): v is string => typeof v === "string");
      else if (typeof valor === "string") campos[campo] = [valor];
    }
  }
  return campos;
}

/** Roda a chamada e converte qualquer falha num ErroDeApi com mensagem que diz o que fazer. */
async function chamar<T>(
  queryClient: QueryClient,
  fazer: () => Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  let resposta: { data?: T; error?: unknown; response: Response };
  try {
    resposta = await fazer();
  } catch {
    throw new ErroDeApi(MENSAGEM_REDE);
  }
  const { data, error, response } = resposta;
  if (response.ok) return data as T;
  if (response.status === 401 || response.status === 403) {
    // Sessão expirada: a rota protegida leva para /entrar.
    queryClient.setQueryData(["sessao"], null);
    throw new ErroDeApi("Sua sessão expirou. Entre de novo.");
  }
  if (response.status === 400) {
    const campos = errosPorCampo(error);
    const detalhe = mensagemDeErro(error, "");
    if (detalhe || Object.keys(campos).length > 0) {
      throw new ErroDeApi(detalhe || "Corrija os campos indicados e tente de novo.", campos);
    }
  }
  if (response.status === 429) {
    throw new ErroDeApi("Muitas tentativas seguidas. Espere um minuto e tente de novo.");
  }
  if (response.status >= 500) {
    throw new ErroDeApi("O servidor teve um problema. Tente de novo em instantes.");
  }
  throw new ErroDeApi(mensagemDeErro(error, MENSAGEM_REDE));
}

export function useTipos() {
  const qc = useQueryClient();
  return useQuery({
    queryKey: ["tipos-de-agente"],
    queryFn: () => chamar(qc, () => api.GET("/api/tipos-de-agente/")),
  });
}

export function useClientes() {
  const qc = useQueryClient();
  return useQuery({
    queryKey: ["clientes"],
    queryFn: () => chamar(qc, () => api.GET("/api/clientes/")),
  });
}

export function useContas() {
  const qc = useQueryClient();
  return useQuery({
    queryKey: ["contas-agente"],
    queryFn: () => chamar(qc, () => api.GET("/api/contas-agente/")),
  });
}

export type DadosDaConta = {
  nome: string;
  tipo: string;
  cliente: string | null;
  limite_simultaneo: number;
  credenciais?: Record<string, string>;
};

export function useTestarDados() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: { tipo: string; credenciais: Record<string, string> }) =>
      chamar(qc, () => api.POST("/api/contas-agente/testar/", { body: dados })),
  });
}

export function useTestarConta() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      chamar(qc, () => api.POST("/api/contas-agente/{id}/testar/", { params: { path: { id } } })),
    onSettled: () => qc.invalidateQueries({ queryKey: ["contas-agente"] }),
  });
}

export function useSalvarConta(id?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: DadosDaConta) =>
      id
        ? chamar(qc, () =>
            api.PATCH("/api/contas-agente/{id}/", { params: { path: { id } }, body: dados }),
          )
        : chamar(qc, () => // O gerador de tipos exige os campos só de leitura no corpo do POST; o servidor os ignora.
          api.POST("/api/contas-agente/", { body: dados as Conta })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["contas-agente"] }),
  });
}

export function useExcluirConta() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      chamar(qc, () => api.DELETE("/api/contas-agente/{id}/", { params: { path: { id } } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["contas-agente"] }),
  });
}
