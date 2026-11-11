import {
  Alert,
  Button,
  Group,
  Modal,
  NativeSelect,
  NumberInput,
  Paper,
  Stack,
  Switch,
  Text,
  TextInput,
} from "@mantine/core";
import { useId, useState } from "react";
import { camposDoErro } from "../api/campos";
import type { Conta, TipoDeAgente } from "../contas/api";
import {
  ETAPA_OBRIGATORIA,
  ErroDeApi,
  type EtapaDaApi,
  ORDEM_DAS_ETAPAS,
  PAPEL_DA_ETAPA,
  type Predefinicao,
  type RotulosDeEtapas,
  type TipoDePapel,
  etapasDe,
  useSalvarPredefinicao,
} from "./api";

type Linha = {
  chave: string;
  ativa: boolean;
  contaId: string;
  modelo: string;
  gatilho: string;
  minutos: number | "";
};

const ROTULO_DO_PAPEL: Record<TipoDePapel, string> = {
  conta: "Conta de agente",
  humano: "Humano",
  central: "Central",
};

function linhasIniciais(predefinicao: Predefinicao): Linha[] {
  const existentes = etapasDe(predefinicao);
  const por = new Map(existentes.map((e) => [e.chave, e]));
  // Sempre na ordem canônica: o servidor recusa qualquer outra, e a ordem salva já é canônica.
  return ORDEM_DAS_ETAPAS.map((chave) => {
    const e = por.get(chave);
    return {
      chave,
      ativa: Boolean(e),
      contaId: e?.papel.conta_id ?? "",
      modelo: e?.papel.modelo ?? "",
      gatilho: e?.gatilho ?? "anterior_concluida",
      minutos: e?.temporizador_minutos ?? "",
    };
  });
}

function paraApi(linha: Linha): EtapaDaApi {
  const tipo = PAPEL_DA_ETAPA[linha.chave] ?? "central";
  const papel: EtapaDaApi["papel"] = { tipo };
  if (tipo === "conta") {
    papel.conta_id = linha.contaId;
    if (linha.modelo.trim()) papel.modelo = linha.modelo.trim();
  }
  const etapa: EtapaDaApi = {
    chave: linha.chave,
    papel,
    gatilho: linha.gatilho,
  };
  if (linha.gatilho === "temporizador" && linha.minutos !== "") etapa.temporizador_minutos = linha.minutos;
  return etapa;
}

/** Separa os erros do servidor: os que citam «Etapa <chave>:» vão para a etapa; o resto fica em geral. */
function distribuirErros(
  erro: Error | null,
  rotuloDaEtapa: (chave: string) => string,
): { porEtapa: Record<string, string[]>; gerais: string[]; nome: string[] } {
  const porEtapa: Record<string, string[]> = {};
  const gerais: string[] = [];
  if (!erro) return { porEtapa, gerais, nome: [] };
  const mensagens: string[] = [];
  const nome = camposDoErro(erro).nome ?? [];
  if (erro instanceof ErroDeApi) {
    for (const [campo, lista] of Object.entries(erro.campos)) if (campo !== "nome") mensagens.push(...lista);
    if (mensagens.length === 0 || !Object.keys(erro.campos).length) mensagens.push(erro.message);
  } else {
    mensagens.push(erro.message);
  }
  for (const m of mensagens) {
    const achou = /^Etapa (\w+):/.exec(m);
    if (achou && ORDEM_DAS_ETAPAS.includes(achou[1])) (porEtapa[achou[1]] ??= []).push(m);
    else gerais.push(m.replace(/\b(?:publicar_tasks|implementar|revisar|merge|promover)\b/g, rotuloDaEtapa));
  }
  return { porEtapa, gerais, nome };
}

type Props = {
  predefinicao: Predefinicao;
  usos: number;
  rotulos: RotulosDeEtapas;
  tipos: TipoDeAgente[];
  contas: Conta[];
  onFechar: () => void;
};

export function EditorPredefinicao({ predefinicao, usos, rotulos, tipos, contas, onFechar }: Props) {
  const salvar = useSalvarPredefinicao(predefinicao.id);
  const prefixo = useId();
  const [nome, setNome] = useState(predefinicao.nome);
  const [metodo, setMetodo] = useState(predefinicao.metodo ?? "superpowers");
  const [mergeAutonomo, setMergeAutonomo] = useState(predefinicao.merge_autonomo ?? true);
  const [linhas, setLinhas] = useState<Linha[]>(() => linhasIniciais(predefinicao));
  const rotuloDaEtapa = (chave: string) => rotulos.etapas.find((e) => e.chave === chave)?.rotulo ?? chave;
  const { porEtapa, gerais, nome: errosDoNome } = distribuirErros(salvar.error, rotuloDaEtapa);
  const sugestoes = (contaId: string) => {
    const conta = contas.find((c) => c.id === contaId);
    return tipos.find((t) => t.tipo === conta?.tipo)?.modelos_sugeridos ?? [];
  };
  const mudar = (chave: string, mudanca: Partial<Linha>) =>
    setLinhas((atual) => atual.map((l) => (l.chave === chave ? { ...l, ...mudanca } : l)));

  const ativas = linhas.filter((l) => l.ativa);
  const contaFaltando = ativas.some((l) => PAPEL_DA_ETAPA[l.chave] === "conta" && !l.contaId);

  return (
    <Modal opened onClose={onFechar} title={`Editar «${predefinicao.nome}»`} size="xl" centered>
      <Stack>
        {usos > 0 && (
          <Alert color="yellow">{`Vale na hora para ${usos} projeto(s), a partir da próxima etapa de cada um.`}</Alert>
        )}
        {gerais.map((m) => (
          <Alert color="red" role="alert" key={m}>
            {m}
          </Alert>
        ))}
        <TextInput
          label="Nome"
          value={nome}
          maxLength={120}
          error={errosDoNome.length ? errosDoNome.join(" ") : undefined}
          onChange={(e) => setNome(e.currentTarget.value)}
        />
        <NativeSelect
          label="Método"
          data={rotulos.metodos.map((m) => ({
            value: m.chave,
            label: m.rotulo,
          }))}
          value={metodo}
          onChange={(e) => setMetodo(e.currentTarget.value)}
        />
        {linhas.map((linha) => {
          const tipo = PAPEL_DA_ETAPA[linha.chave] ?? "central";
          const lista = `${prefixo}-modelos-${linha.chave}`;
          return (
            <Paper withBorder p="sm" key={linha.chave} data-etapa={linha.chave}>
              <Stack gap="xs">
                <Group justify="space-between" wrap="wrap">
                  <Switch
                    label={rotuloDaEtapa(linha.chave)}
                    checked={linha.ativa}
                    disabled={linha.chave === ETAPA_OBRIGATORIA}
                    onChange={(e) => mudar(linha.chave, { ativa: e.currentTarget.checked })}
                  />
                </Group>
                {linha.ativa && (
                  <Group align="flex-end" wrap="wrap">
                    <NativeSelect
                      label="Papel"
                      data={[{ value: tipo, label: ROTULO_DO_PAPEL[tipo] }]}
                      value={tipo}
                      onChange={() => {}}
                    />
                    {tipo === "conta" && (
                      <>
                        <NativeSelect
                          label="Conta"
                          data={[
                            { value: "", label: "Escolha uma conta" },
                            ...contas.map((c) => ({
                              value: c.id,
                              label: c.nome,
                            })),
                          ]}
                          value={linha.contaId}
                          onChange={(e) =>
                            mudar(linha.chave, {
                              contaId: e.currentTarget.value,
                            })
                          }
                        />
                        <div>
                          <TextInput
                            label="Modelo"
                            description="Vazio usa o modelo padrão da conta."
                            list={lista}
                            maxLength={64}
                            value={linha.modelo}
                            onChange={(e) =>
                              mudar(linha.chave, {
                                modelo: e.currentTarget.value,
                              })
                            }
                          />
                          <datalist id={lista}>
                            {sugestoes(linha.contaId).map((m) => (
                              <option key={m} value={m} />
                            ))}
                          </datalist>
                        </div>
                      </>
                    )}
                    <NativeSelect
                      label="Gatilho"
                      data={rotulos.gatilhos.map((g) => ({
                        value: g.chave,
                        label: g.rotulo,
                      }))}
                      value={linha.gatilho}
                      onChange={(e) => mudar(linha.chave, { gatilho: e.currentTarget.value })}
                    />
                    {linha.gatilho === "temporizador" && (
                      <NumberInput
                        label="Minutos"
                        min={1}
                        allowDecimal={false}
                        value={linha.minutos}
                        onChange={(v) =>
                          mudar(linha.chave, {
                            minutos: typeof v === "number" ? v : "",
                          })
                        }
                      />
                    )}
                  </Group>
                )}
                {(porEtapa[linha.chave] ?? []).map((m) => (
                  <Text key={m} c="red" size="sm" role="alert">
                    {m}
                  </Text>
                ))}
              </Stack>
            </Paper>
          );
        })}
        <Switch
          label={mergeAutonomo ? "Merge autônomo" : "Merge com ok humano"}
          checked={mergeAutonomo}
          onChange={(e) => setMergeAutonomo(e.currentTarget.checked)}
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={onFechar}>
            Cancelar
          </Button>
          <Button
            loading={salvar.isPending}
            disabled={contaFaltando || !nome.trim()}
            onClick={() =>
              salvar.mutate(
                {
                  nome: nome.trim(),
                  metodo,
                  etapas: ativas.map(paraApi),
                  merge_autonomo: mergeAutonomo,
                },
                { onSuccess: onFechar },
              )
            }
          >
            Salvar
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
