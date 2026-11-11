import { Alert, Button, Group, Modal, NativeSelect, NumberInput, Paper, Stack, Switch, Text, TextInput } from "@mantine/core";
import { useId, useState } from "react";
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
  const chaves = [...existentes.map((e) => e.chave), ...ORDEM_DAS_ETAPAS.filter((c) => !por.has(c))];
  return chaves.map((chave) => {
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
  const etapa: EtapaDaApi = { chave: linha.chave, papel, gatilho: linha.gatilho };
  if (linha.gatilho === "temporizador" && linha.minutos !== "") etapa.temporizador_minutos = linha.minutos;
  return etapa;
}

/** Separa os erros do servidor: os que citam «Etapa <chave>:» vão para a etapa; o resto fica em geral. */
function distribuirErros(erro: Error | null): { porEtapa: Record<string, string[]>; gerais: string[] } {
  const porEtapa: Record<string, string[]> = {};
  const gerais: string[] = [];
  if (!erro) return { porEtapa, gerais };
  const mensagens: string[] = [];
  if (erro instanceof ErroDeApi) {
    for (const lista of Object.values(erro.campos)) mensagens.push(...lista);
    if (mensagens.length === 0 || !Object.keys(erro.campos).length) mensagens.push(erro.message);
  } else {
    mensagens.push(erro.message);
  }
  for (const m of mensagens) {
    const achou = /^Etapa (\w+):/.exec(m);
    if (achou && ORDEM_DAS_ETAPAS.includes(achou[1])) (porEtapa[achou[1]] ??= []).push(m);
    else gerais.push(m);
  }
  return { porEtapa, gerais };
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
  const [metodo, setMetodo] = useState(predefinicao.metodo ?? "superpowers");
  const [mergeAutonomo, setMergeAutonomo] = useState(predefinicao.merge_autonomo ?? true);
  const [linhas, setLinhas] = useState<Linha[]>(() => linhasIniciais(predefinicao));
  const { porEtapa, gerais } = distribuirErros(salvar.error);

  const rotuloDaEtapa = (chave: string) => rotulos.etapas.find((e) => e.chave === chave)?.rotulo ?? chave;
  const sugestoes = (contaId: string) => {
    const conta = contas.find((c) => c.id === contaId);
    return tipos.find((t) => t.tipo === conta?.tipo)?.modelos_sugeridos ?? [];
  };
  const mudar = (chave: string, mudanca: Partial<Linha>) =>
    setLinhas((atual) => atual.map((l) => (l.chave === chave ? { ...l, ...mudanca } : l)));
  const mover = (indice: number, delta: number) =>
    setLinhas((atual) => {
      const novo = [...atual];
      [novo[indice], novo[indice + delta]] = [novo[indice + delta], novo[indice]];
      return novo;
    });

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
        <NativeSelect
          label="Método"
          data={rotulos.metodos.map((m) => ({ value: m.chave, label: m.rotulo }))}
          value={metodo}
          onChange={(e) => setMetodo(e.currentTarget.value)}
        />
        {linhas.map((linha, i) => {
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
                  <Group gap="xs">
                    <Button
                      size="compact-sm"
                      variant="default"
                      aria-label={`Subir ${rotuloDaEtapa(linha.chave)}`}
                      disabled={i === 0}
                      onClick={() => mover(i, -1)}
                    >
                      Subir
                    </Button>
                    <Button
                      size="compact-sm"
                      variant="default"
                      aria-label={`Descer ${rotuloDaEtapa(linha.chave)}`}
                      disabled={i === linhas.length - 1}
                      onClick={() => mover(i, 1)}
                    >
                      Descer
                    </Button>
                  </Group>
                </Group>
                {linha.ativa && (
                  <Group align="flex-end" wrap="wrap">
                    <NativeSelect label="Papel" data={[{ value: tipo, label: ROTULO_DO_PAPEL[tipo] }]} value={tipo} onChange={() => {}} />
                    {tipo === "conta" && (
                      <>
                        <NativeSelect
                          label="Conta"
                          data={[{ value: "", label: "Escolha uma conta" }, ...contas.map((c) => ({ value: c.id, label: c.nome }))]}
                          value={linha.contaId}
                          onChange={(e) => mudar(linha.chave, { contaId: e.currentTarget.value })}
                        />
                        <div>
                          <TextInput
                            label="Modelo"
                            description="Vazio usa o modelo padrão da conta."
                            list={lista}
                            maxLength={64}
                            value={linha.modelo}
                            onChange={(e) => mudar(linha.chave, { modelo: e.currentTarget.value })}
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
                      data={rotulos.gatilhos.map((g) => ({ value: g.chave, label: g.rotulo }))}
                      value={linha.gatilho}
                      onChange={(e) => mudar(linha.chave, { gatilho: e.currentTarget.value })}
                    />
                    {linha.gatilho === "temporizador" && (
                      <NumberInput
                        label="Minutos"
                        min={1}
                        allowDecimal={false}
                        value={linha.minutos}
                        onChange={(v) => mudar(linha.chave, { minutos: typeof v === "number" ? v : "" })}
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
            disabled={contaFaltando}
            onClick={() =>
              salvar.mutate({ metodo, etapas: ativas.map(paraApi), merge_autonomo: mergeAutonomo }, { onSuccess: onFechar })
            }
          >
            Salvar
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
