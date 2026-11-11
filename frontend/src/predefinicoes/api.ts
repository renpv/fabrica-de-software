import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { chamar } from "../api/chamar";
import { api } from "../api/cliente";
import type { components } from "../api/schema";

export { useContas, useTipos } from "../contas/api";
export { usePredefinicoes, useProjetos } from "../plataformas/api";
export { ErroDeApi } from "../api/chamar";

export type Predefinicao = components["schemas"]["Predefinicao"];
export type RotulosDeEtapas = components["schemas"]["EtapasEGatilhos"];

export type TipoDePapel = "conta" | "humano" | "central";

/** Uma etapa como o back-end guarda em `Predefinicao.etapas` (o schema da API a declara como JSON livre). */
export type EtapaDaApi = {
  chave: string;
  papel: { tipo: TipoDePapel; conta_id?: string; modelo?: string };
  gatilho: string;
  temporizador_minutos?: number;
};

/**
 * Papel permitido em cada etapa. A API não expõe esta regra (só existe em
 * `backend/apps/fluxos/servicos.py::_validar_papel`), então este espelho precisa acompanhar
 * o back-end; o servidor continua sendo quem valida.
 */
export const PAPEL_DA_ETAPA: Record<string, TipoDePapel> = {
  publicar_tasks: "central",
  implementar: "conta",
  revisar: "conta",
  merge: "central",
  promover: "humano",
};

/** Etapas na ordem exigida pelo servidor; `implementar` é obrigatória. */
export const ORDEM_DAS_ETAPAS = ["publicar_tasks", "implementar", "revisar", "merge", "promover"];
export const ETAPA_OBRIGATORIA = "implementar";

export function etapasDe(predefinicao: Predefinicao): EtapaDaApi[] {
  return Array.isArray(predefinicao.etapas) ? (predefinicao.etapas as EtapaDaApi[]) : [];
}

export function useRotulos() {
  const qc = useQueryClient();
  return useQuery({
    queryKey: ["etapas-e-gatilhos"],
    queryFn: () => chamar(qc, () => api.GET("/api/etapas-e-gatilhos/")),
  });
}

export type DadosDaPredefinicao = { metodo: string; etapas: EtapaDaApi[]; merge_autonomo: boolean };

export function useSalvarPredefinicao(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: DadosDaPredefinicao) =>
      chamar(qc, () => api.PATCH("/api/predefinicoes/{id}/", { params: { path: { id } }, body: dados })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["predefinicoes"] }),
  });
}

export function useCriarPadrao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: { executor: string; revisor: string }) =>
      chamar(qc, () => api.POST("/api/predefinicoes/padrao/", { body: dados })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["predefinicoes"] }),
  });
}

export function useDuplicar(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (nome: string) =>
      chamar(qc, () => api.POST("/api/predefinicoes/{id}/duplicar/", { params: { path: { id } }, body: { nome } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["predefinicoes"] }),
  });
}
