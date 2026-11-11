import type { QueryClient } from "@tanstack/react-query";

/**
 * Remove do cache tudo que pertence ao usuário (contas, conexões, projetos, predefinições...),
 * menos a consulta da sessão, que a tela ainda observa (`clear()` a desligaria).
 * Roda no login, no logout e quando a sessão é perdida, para outra pessoa nunca ver dados do dono anterior.
 */
export function limparDadosDoUsuario(queryClient: QueryClient) {
  queryClient.removeQueries({ predicate: (consulta) => consulta.queryKey[0] !== "sessao" });
}
