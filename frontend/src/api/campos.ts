import { ErroDeApi } from "./chamar";

type Opcoes = {
  /** Nome em pt-BR de cada campo, para dizer onde está o erro (padrão: a própria chave). */
  rotulos?: Record<string, string>;
  /** Campos que a tela já mostra junto do próprio campo e não devem repetir aqui. */
  exceto?: string[];
};

/** Erros por campo de um 400 (vazio para qualquer outro erro). */
export function camposDoErro(erro: unknown): Record<string, string[]> {
  return erro instanceof ErroDeApi ? erro.campos : {};
}

/**
 * Mensagem do erro seguida dos erros por campo ("Executor: Esta conta não existe."),
 * para telas sem um lugar próprio para cada campo.
 */
export function mensagemComCampos(erro: Error, { rotulos = {}, exceto = [] }: Opcoes = {}): string {
  const extras = Object.entries(camposDoErro(erro))
    .filter(([campo]) => !exceto.includes(campo))
    .flatMap(([campo, mensagens]) => mensagens.map((m) => `${rotulos[campo] ?? campo}: ${m}`));
  return [erro.message, ...extras].join(" ");
}
