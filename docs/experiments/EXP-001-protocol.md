# EXP-001 — Bagé 2023: cobertura da terra e meteorologia observada

**Status:** aceito e executado na v0.1.2  
**Protocolo:** 1.0.0  
**Data:** 2026-11-07  
**Decisão arquitetural:** [ADR-003](../ADR-003-PRIMEIRA-INTEGRACAO.md)

## Pergunta

Quais classes de cobertura e uso da terra são mapeadas para Bagé em 2023 e quais condições de temperatura e precipitação foram observadas pela estação A827 em janeiro; essas descrições podem ser diretamente comparadas?

A pergunta não pressupõe associação, influência ou causalidade. O resultado admissível inclui incompatibilidade ou evidência insuficiente.

## Recorte e justificativa

- **Território de referência:** município de Bagé/RS, código IBGE `4301602`.
- **Meteorologia:** estação automática INMET A827, coordenadas `-31.34777777, -54.01333333`, altitude informada de 226,19 m.
- **Tempo:** classificação MapBiomas anual de 2023 e observações INMET de `2023-01-01T00:00:00Z` a `2023-01-31T23:00:00Z`.
- **Justificativa operacional:** ambas as fontes possuem artefatos públicos, identificáveis e efetivamente acessíveis para o recorte. A seleção não afirma que A827 represente Bagé nem que janeiro represente o ano.

## Fontes reais

1. **MapBiomas Brasil — Coleção 11, tabela municipal v1.** A fonte oficial recomenda a coleção mais recente e descreve a tabela municipal como estatística de área em hectares por classe. Dados sob CC BY 4.0 com atribuição. Página: <https://brasil.mapbiomas.org/iniciativas-e-produtos/cobertura-e-uso-da-terra/cobertura-30m/cobertura/>.
2. **INMET — Dados Históricos Anuais 2023.** O INMET declara os dados públicos e gratuitos, em UTC, e informa que dados de estações automáticas são brutos e não passam por consistência. Página: <https://portal.inmet.gov.br/dadoshistoricos>. Orientações: <https://portal.inmet.gov.br/noticias/saiba-como-acessar-os-dados-meteorol%C3%B3gicos-dispon%C3%ADveis-no-site-do-inmet>.

URLs, tamanhos, membros internos e SHA-256 estão em [`data/exp001/sources.json`](../../data/exp001/sources.json). Os arquivos integrais de 78 MB e 107 MB não são versionados; os subconjuntos reais de 2,2 KB e 1,4 KB são versionados com atribuição e hashes.

## Contrato e operações

O schema [`integration-record-v1.schema.json`](../../contracts/integration-record-v1.schema.json) exige identidade, versão, proveniência, hashes distintos do artefato e do subconjunto, semântica, tempos, suporte espacial, qualidade e advertências. `unknown_values_are_zero` deve ser `false`.

Operações determinísticas:

1. `mapbiomas-select-geocode-year-v1`: selecionar `geocode=4301602` e `year_column=y2023` da planilha municipal.
2. `inmet-hourly-to-daily-v1`: selecionar A827 em janeiro de 2023; reconhecer `""`, `9999` e `Null` como ausentes; somar precipitação e calcular média/mínimo/máximo de temperatura apenas sobre valores presentes.
3. `compatibility-v1`: comparar suporte e granularidade, sem comparar valores de natureza diferente.
4. Registrar duas evidências como `contextualizes`, uma objeção espacial e uma decisão explícita de não inferência.

O modo `prepare` reconstrói byte a byte os subconjuntos a partir dos ZIPs oficiais:

```bash
python3 tools/exp001.py prepare \
  --mapbiomas-archive /caminho/MAPBIOMAS_BRAZIL-COL.11-BIOME_STATE_MUNICIPALITY.zip \
  --inmet-archive /caminho/2023.zip \
  --output /tmp/exp001-prepared
```

## Execução reproduzível

Em um checkout limpo, sem rede e usando os subconjuntos versionados:

```bash
./run.sh test
./run.sh experiment
```

O segundo comando usa banco isolado em `var/exp001/tessitura.sqlite3`, executa a importação duas vezes, exige idempotência e grava `report.json` e `dossier.md` em `var/exp001/output/`. Não modifica o banco padrão nem outro repositório.

## Critérios de inclusão e exclusão

Incluídos:

- todas as 13 classes com área informada para Bagé em `y2023`;
- todas as 744 horas de janeiro de 2023 da A827;
- temperatura do ar e precipitação horárias, com agregação documentada;
- metadados de estação e advertências publicadas pelas fontes.

Excluídos:

- outros anos, meses, estações, variáveis e geometrias;
- pixels MapBiomas e geometria municipal;
- interpolação da estação para o município;
- correlação, teste de hipótese, causalidade, predição e pontuação de confiabilidade.

## Objeções a priori

1. A827 é um ponto; MapBiomas está agregado ao polígono municipal. Os suportes não são intercambiáveis.
2. Janeiro horário/diário e classificação anual apenas se sobrepõem; não possuem granularidade equivalente.
3. A classificação é produto metodológico e as observações automáticas são declaradas brutas; nenhuma é “verdade de campo” automática.
4. Coincidência em Bagé e 2023 não estabelece relação entre cobertura e meteorologia.

## Condições de fracasso

- hash de artefato ou subconjunto divergir;
- schema aceitar ausência convertida em zero;
- cálculo não reproduzir os valores contratados;
- segunda execução aumentar contagens lógicas;
- estação ser tratada como representação municipal;
- dossiê promover associação ou causalidade.

O resultado `contextual_only` é sucesso científico do protocolo. Ocultar a incompatibilidade seria fracasso.

## Fora do escopo

Conector online, alteração de MapBiomas/INMET/MÉTIS/EVIDA, nova ontologia, proposições, PostGIS, mapa, dashboard, LLM, autenticação e generalização para outros territórios.
