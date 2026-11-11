import type { QueryClient } from "@tanstack/react-query";
import { limparDadosDoUsuario } from "./cache";
import { mensagemDeErro } from "./cliente";

export const MENSAGEM_REDE = "Não foi possível falar com o servidor. Verifique a conexão e tente de novo.";

/** Erro de uma chamada, já com texto em pt-BR; `campos` traz os erros por campo de um 400. */
export class ErroDeApi extends Error {
  campos: Record<string, string[]>;
  constructor(mensagem: string, campos: Record<string, string[]> = {}) {
    super(mensagem);
    this.campos = campos;
  }
}

/** Falha de rede: nem chegou resposta do servidor. */
export class ErroDeRede extends ErroDeApi {}

/** Só falha de rede merece nova tentativa (uma só); resposta do servidor aparece na hora. */
export function deveTentarDeNovo(falhas: number, erro: unknown): boolean {
  return falhas < 1 && (erro instanceof ErroDeRede || erro instanceof TypeError);
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
export async function chamar<T>(
  queryClient: QueryClient,
  fazer: () => Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  let resposta: { data?: T; error?: unknown; response: Response };
  try {
    resposta = await fazer();
  } catch {
    throw new ErroDeRede(MENSAGEM_REDE);
  }
  const { data, error, response } = resposta;
  if (response.ok) return data as T;
  if (response.status === 401 || response.status === 403) {
    // Sessão expirada: a rota protegida leva para /entrar, e nada do dono anterior fica no cache.
    limparDadosDoUsuario(queryClient);
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
    // O 502 das integrações traz um `detail` que diz o que fazer; o 500 do Django vem em HTML, sem ele.
    throw new ErroDeApi(mensagemDeErro(error, "O servidor teve um problema. Tente de novo em instantes."));
  }
  throw new ErroDeApi(mensagemDeErro(error, MENSAGEM_REDE));
}
