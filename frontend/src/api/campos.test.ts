import { ErroDeApi } from "./chamar";
import { mensagemComCampos } from "./campos";

describe("mensagemComCampos", () => {
  it("junta a mensagem com os erros por campo, com o rótulo em pt-BR", () => {
    const erro = new ErroDeApi("Corrija os campos indicados e tente de novo.", {
      executor: ["Esta conta não existe."],
      revisor: ["Este campo é obrigatório."],
    });
    expect(mensagemComCampos(erro, { rotulos: { executor: "Executor", revisor: "Revisor" } })).toBe(
      "Corrija os campos indicados e tente de novo. Executor: Esta conta não existe. Revisor: Este campo é obrigatório.",
    );
  });

  it("omite os campos que a tela já mostra no próprio campo", () => {
    const erro = new ErroDeApi("Corrija.", { nome: ["Obrigatório."], limite: ["Alto demais."] });
    expect(mensagemComCampos(erro, { exceto: ["nome"] })).toBe("Corrija. limite: Alto demais.");
  });

  it("devolve só a mensagem quando não há campos ou o erro é comum", () => {
    expect(mensagemComCampos(new ErroDeApi("Falhou."))).toBe("Falhou.");
    expect(mensagemComCampos(new Error("Falhou de outro jeito."))).toBe("Falhou de outro jeito.");
  });
});
