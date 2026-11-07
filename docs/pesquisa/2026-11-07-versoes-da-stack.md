# Versões da stack (Node, Python, Django, PostgreSQL, Docker, Compose, gh, uv)

Data de acesso: 2026-11-07. Pesquisa feita por consulta às fontes oficiais (e à API do endoflife.date como apoio).

## Resumo

- Tudo o que a imagem do agente instalou é a versão estável mais recente de cada ferramenta hoje: Docker 29.9.3, Compose 5.7.0, gh 2.103.3, uv 0.13.7 [F9][F10][F11][F12]. Node 22.23.4 é o último da linha 22 [F1].
- **Atenção em Node:** a linha 22 já está em Maintenance e termina em 2027-04-30 [F2]. Há um aviso oficial de novo security release (nível HIGH) para as linhas 26, 24 e 22, previsto para 11/11/2026 [F4]. Ou seja, o 22.23.4 vai ficar desatualizado em poucos dias.
- Para um projeto novo, a recomendação é: **Node 26 (LTS ativa)**, **Python 3.14**, **Django 5.2 LTS** (troca para 6.x ainda não compensa; ver seção), **PostgreSQL 18** (17 é aceitável), e Docker/Compose/gh/uv sem pinar na imagem do agente (mas pinar uv e imagens base dentro do projeto).
- Não confirmei: suporte explícito e testado do Django 5.2 ao PostgreSQL 18 (a wiki oficial só infere), a data do Django 6.2 LTS e os CVEs corrigidos pelo security release de Node de 11/11 (ainda não publicado).

## Tabela

| Item | Instalada | Mais recente (07/11/2026) | Status/suporte | Segurança | Recomendação |
|---|---|---|---|---|---|
| Node | 22.23.4 | 26.13.0 (LTS), 24.22.2, 22.23.4 | 26: Active LTS até 2027-10-20, EOL 2029-04-30. 24: Maintenance desde 2026-10-20, EOL 2028-04-30. 22: Maintenance, EOL 2027-04-30 | 22.23.4 corrige o release de 21/10/2026. Novo release HIGH anunciado para 11/11/2026 (22.x afetada) | Trocar para Node 26 (`.nvmrc` = 26). Vite 8 pede Node ^20.19 ou >=22.12, então 26 atende |
| Python | 3.13 (uv) | 3.15.2 (lançado 2026-10-09), 3.14.10, 3.13.18 | 3.15 e 3.14: bugfix. 3.13: só segurança (EOL 2029-10). 3.10: EOL desde 2026-10-01 | Não verifiquei CVE por micro versão. Usar sempre o último micro | Fixar 3.14 (`.python-version`). Não usar 3.15 com Django 5.2 (não suportado) |
| Django | n/a (projeto usa 5.2) | 6.1.3; 6.0.10; 5.2.19 (LTS) | 5.2 LTS: segurança até abril/2028. 6.1: até dez/2027. 6.0: até abr/2027 | 3 releases de segurança em 5.2 em out/nov 2026; 5.2.19 (03/11/2026) é o atual | Ficar no 5.2 LTS, sempre no último patch (>=5.2.19). Planejar 6.2 LTS (data não confirmada) |
| PostgreSQL | 17 (planejado) | 18.6, 17.11, 16.15, 15.19, 14.24 | 18: até 2030-11-14. 17: até 2029-11-08. 14: EOL 2026-11-12 | Acompanhar minors (releases de 10/08/2026 e 11/08/2026) | PostgreSQL 18 em projeto novo (17 também serve). Imagem `postgres:18` |
| Docker Engine | 29.9.3 | 29.9.3 (29.10.0-rc.1 é pré-release) | Sem política de suporte publicada por linha (não confirmado) | 29.9.3 é justamente a correção de 4 CVEs de 03/11/2026. Nenhum aviso aberto conhecido para ela | Não fixar na imagem do agente; manter atualizado |
| Docker Compose | 5.7.0 | 5.7.0 (02/11/2026) | Linha 5.x ativa | Único aviso listado (CVE-2025-62725) foi corrigido em 2.40.2 | Não fixar; registrar a versão no log |
| gh | 2.103.3 | 2.103.3 (26/10/2026) | n/a | Avisos de set/2026 corrigidos em 2.102.0 | Não fixar |
| uv | 0.13.7 | 0.13.7 (03/11/2026) | Pré-1.0, sem LTS | Aviso de out/2026 corrigido em 0.13.4 | Não fixar no agente; no projeto, fixar `required-version` e a imagem do uv |

## Node

- Estável mais recente: 26.13.0 (LTS, 2026-10-28); 24.22.2; 22.23.4 (2026-10-21) [F1].
- Calendário oficial: v26 LTS desde 2026-10-28, Maintenance em 2027-10-20, fim em 2029-04-30. v24 em Maintenance desde 2026-10-20, fim em 2028-04-30. v22 em Maintenance desde 2025-10-21, fim em 2027-04-30. v25 acabou em 2026-06-01 [F2].
- Segurança: o release de 21/10/2026 (severidade máxima High) corrige 10 CVEs, entre eles bypass de verificação de hostname em TLS e escrita fora dos limites no decodificador Brotli. A correção na linha 22 é justamente a 22.23.4 [F3]. Logo, 22.23.4 está corrigido para aquele release.
- Mas há um pré-aviso oficial (atualizado em 03/11/2026) de novo security release para 26.x, 24.x e 22.x, esperado em ou logo depois de 11/11/2026, com severidade máxima High. A página não traz versões nem CVEs ainda [F4].
- Compatibilidade: Vite 8.3.6 (atual) declara `engines.node: ^20.19.0 || >=22.12.0`; `@vitejs/plugin-react` 6.2.1 tem o mesmo requisito; React atual é 19.3.1 e TypeScript 7.0.2 [F5]. Node 22.23.4 atende, e Node 26 também.
- Recomendação: `.nvmrc` com `26` e, no Dockerfile do front, `FROM node:26-...` (ou a tag LTS equivalente). Se a imagem do agente precisar continuar na 22, é aceitável por ora, mas ela sai de suporte em 2027-04-30. O NodeSource tem script `setup_26.x` (não verifiquei se já existe; confirmar).

## Python

- Devguide: 3.15 (bugfix, primeira versão 2026-10-09, EOL 2031-10), 3.14 (bugfix, EOL 2030-10), 3.13 (security, EOL 2029-10), 3.12 (security, EOL 2028-10), 3.11 (security, EOL 2027-10), 3.10 (EOL 2026-10-01) [F6].
- Últimos micro (endoflife.date, apoio): 3.15.2, 3.14.10, 3.13.18, todos de 2026-10-25 [F7]. O `uv python install 3.13` pega o último 3.13.x disponível no momento; não confirmei qual micro foi instalado (rodar `python --version`).
- Django 5.2 suporta Python 3.10 a 3.14 (3.14 desde 5.2.8). Não suporta 3.15 [F8]. Django 6.1 suporta 3.12 a 3.15 (3.15 desde 6.1.3) [F13].
- Recomendação: Python 3.14 em `.python-version`, na imagem `python:3.14-slim` e em `requires-python = ">=3.14,<3.15"`. A 3.13 também serve (só segurança), mas dá menos tempo de vida (até 2029-10 contra 2030-10).

## Django 5.2 vs 6.x

- Última: 6.1.3 (6.1 saiu em 2026-08-05). 5.2 LTS: 5.2.19. Suporte: 5.2 LTS segurança até abril/2028; 6.0 até abril/2027; 6.1 até dezembro/2027 [F14][F15].
- Segurança: 5.2.19, 6.0.10 e 6.1.3 saíram em 2026-11-03 corrigindo 6 problemas; antes, 5.2.18 em 2026-10-06 corrigiu 4 [F16]. Estar no último patch é obrigatório.
- Django 6.1 exige PostgreSQL 15+, Python 3.12+ e remove vários recursos antigos; muda também o comportamento de `first()`/`last()` e de `union()` [F15].
- Vale trocar agora? Para um projeto novo com horizonte longo, não: 6.1 é versão intermediária, com suporte só até dez/2027, enquanto a 5.2 LTS cobre até abr/2028. O padrão do projeto Django é LTS a cada dois anos e a página de release process cita 6.2 como a próxima LTS [F17], mas a data de lançamento do 6.2 não está confirmada. Recomendo 5.2 LTS agora e migrar para 6.2 LTS quando sair. Não verifiquei a compatibilidade do DRF com Django 6.x (confirmar no changelog do DRF antes de migrar).
- PostgreSQL 18 com Django 5.2: a documentação oficial diz "PostgreSQL 14 e superior" e não cita o 18 [F18]; a wiki oficial de bancos suportados lista o 18 sem versão de remoção (suporte apenas inferido) [F19]. Isso é uma confirmação fraca; testar a suíte contra o 18 no CI.

## PostgreSQL

- Versões atuais: 18.6, 17.11, 16.15, 15.19, 14.24. Fim de suporte: 18 em 2030-11-14, 17 em 2029-11-08, 16 em 2028-11-09, 15 em 2027-11-11, 14 em 2026-11-12 [F20]. Política: 5 anos por versão major; rodar sempre o minor mais novo [F20].
- Django 5.2 aceita 14+; Django 6.1 exige 15+ [F15][F18].
- Recomendação: PostgreSQL 18 para projeto novo (mais 1 ano de vida que o 17), com `image: postgres:18` no Compose (acompanha minors) e teste no CI contra a mesma major. Manter 17 só se já houver dados ou a imagem de produção estiver nele. Observação não verificada: a imagem Docker oficial do postgres 18 mudou o ponto de montagem do volume de dados; conferir a documentação da imagem antes de montar o volume.

## Docker Engine

- Última estável: 29.9.3 (2026-11-03); existe 29.10.0-rc.1 (pré-release, 2026-11-06) [F9][F10].
- As notas de release de 29.9.3 corrigem CVE-2026-116587, CVE-2026-116591, CVE-2026-115538, CVE-2026-115539 e dois avisos do BuildKit [F9]. A versão instalada é exatamente esta, então está corrigida. A API de advisories do moby mostra o último aviso corrigido em 29.8.2 (CVE-2026-92543, de 2026-10-01) [F10]. Não vi aviso aberto para 29.9.3, mas só li as primeiras 100 mil letras da página de notas (falta o final, que é histórico).
- Suporte por linha: a página de notas não declara política nem datas de fim (não confirmado) [F9].
- Recomendação: não fixar na imagem do agente (a última do repositório oficial é a certa e a segurança é corrigida só em releases novos). Em produção, atualizar com regularidade.

## Docker Compose

- Última: v5.7.0 (2026-11-02); anteriores v5.6.1 (2026-10-21), v5.6.0 (2026-10-02) [F11].
- O único aviso listado, CVE-2025-62725, foi corrigido em 2.40.2 [F11], então não afeta a 5.7.0.
- Recomendação: não fixar na imagem do agente. No projeto, usar `docker compose` (plugin v2+) e evitar o campo `version:` no YAML.

## gh

- Última: v2.103.3 (2026-10-26) [F12]. Avisos de set/2026 (inclusive escrita fora do destino por symlink, severidade média) foram corrigidos na 2.102.0 [F12]. Não há aviso aberto para 2.103.3 na API.
- Recomendação: não fixar.

## uv

- Última: 0.13.7 (2026-11-03) [F12]. O aviso de out/2026 (remoção do certificado raiz emSign, alta) foi corrigido em 0.13.4 [F12].
- Recomendação: no agente, não fixar. No projeto, fixar a versão mínima com `required-version` em `pyproject.toml`/`uv.toml` e, no Dockerfile, copiar de `ghcr.io/astral-sh/uv:<versão>` (prática oficial da Astral; o nome da imagem não foi reconferido hoje). Commitar `uv.lock`.

## Onde fixar (projeto novo)

| Onde | O quê |
|---|---|
| `.nvmrc` | `26` |
| `package.json` `engines.node` | `>=22.12` (piso do Vite 8) ou `^26` se quiser rigidez |
| `.python-version` | `3.14` |
| `pyproject.toml` | `requires-python = ">=3.14,<3.15"`, `django>=5.2.19,<5.3`, `[tool.uv] required-version` |
| Dockerfile (back) | `python:3.14-slim` + uv fixado |
| Dockerfile (front) | `node:26-slim` (ou equivalente LTS) |
| docker-compose.yml | `postgres:18` |
| Agente (Docker, Compose, gh, uv) | sem fixar; registrar versões no log do build |

## Perguntas em aberto

1. Data e conteúdo do security release de Node de 2026-11-11 (versões corrigidas e CVEs). Reconferir depois dessa data [F4].
2. Django 5.2 e PostgreSQL 18: suporte só inferido pela wiki [F19]; falta confirmação em nota de release.
3. Data de lançamento do Django 6.2 LTS e compatibilidade do DRF com Django 6.x.
4. Existência de `setup_26.x` no NodeSource e das tags `node:26-*` no Docker Hub (não verificado).
5. Política de suporte por linha do Docker Engine 29.x (não publicada na página consultada).
6. Micro exato do Python instalado pelo `uv python install 3.13` (rodar `python --version`).
7. Mudança do volume de dados na imagem `postgres:18` (de memória; confirmar na página da imagem).

## Fontes

- [F1] https://endoflife.date/api/nodejs.json
- [F2] https://raw.githubusercontent.com/nodejs/Release/main/schedule.json
- [F3] https://nodejs.org/en/blog/vulnerability/october-2026-security-releases
- [F4] https://nodejs.org/en/blog/vulnerability/november-2026-security-releases (e lista em https://nodejs.org/en/blog/vulnerability)
- [F5] https://registry.npmjs.org/vite/latest, https://registry.npmjs.org/@vitejs/plugin-react/latest, https://registry.npmjs.org/react/latest, https://registry.npmjs.org/typescript/latest
- [F6] https://devguide.python.org/versions/
- [F7] https://endoflife.date/api/python.json
- [F8] https://docs.djangoproject.com/en/5.2/faq/install/ e https://docs.djangoproject.com/en/5.2/releases/5.2.8/
- [F9] https://docs.docker.com/engine/release-notes/29/
- [F10] https://api.github.com/repos/moby/moby/releases e https://api.github.com/repos/moby/moby/security-advisories
- [F11] https://api.github.com/repos/docker/compose/releases e https://api.github.com/repos/docker/compose/security-advisories
- [F12] https://api.github.com/repos/cli/cli/releases/latest, https://api.github.com/repos/cli/cli/security-advisories, https://api.github.com/repos/astral-sh/uv/releases/latest, https://api.github.com/repos/astral-sh/uv/security-advisories
- [F13] https://docs.djangoproject.com/en/6.1/faq/install/
- [F14] https://www.djangoproject.com/download/ e https://endoflife.date/api/django.json
- [F15] https://docs.djangoproject.com/en/6.1/releases/6.1/
- [F16] https://www.djangoproject.com/weblog/
- [F17] https://docs.djangoproject.com/en/dev/internals/release-process/
- [F18] https://docs.djangoproject.com/en/5.2/ref/databases/
- [F19] https://code.djangoproject.com/wiki/SupportedDatabaseVersions
- [F20] https://www.postgresql.org/support/versioning/ e https://endoflife.date/api/postgresql.json
