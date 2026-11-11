import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { chamar } from "../api/chamar";
import { api } from "../api/cliente";
import type { components } from "../api/schema";

export type Conta = components["schemas"]["ContaAgente"];
export type TipoDeAgente = components["schemas"]["TipoDeAgente"];
export type Cliente = components["schemas"]["Cliente"];
export type ResultadoTeste = components["schemas"]["ResultadoTeste"];

export { ErroDeApi, MENSAGEM_REDE } from "../api/chamar";

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
