# TESSITURA — Laboratório de trajetórias e relações socioecológicas

**v0.1.2 · C++26 · SQLite WAL · integração científica vertical · web local**

> Faça simples. Depois deixe mais leve. Sempre pronto. Sempre incompleto.

Protótipo funcional, independente, centrado em **situações investigáveis**. Registra perguntas, evidências tipadas com proveniência e tempo, relações explicitamente justificadas e um diário de hipóteses/objeções. Não faz inferência nem confirma causalidade.

## Fedora 44 — início rápido

Instale as dependências no **host Fedora 44 ou na toolbox**, conforme onde pretende compilar/executar:

```bash
sudo dnf install -y gcc-c++ cmake ninja-build boost-devel sqlite-devel openssl-devel python3 python3-jsonschema
```

Depois:

```bash
cd /home/jpereiratrindade/dev/cpp/tessitura
./run.sh test        # Compila e executa teste local ponta a ponta
./run.sh experiment  # Executa o EXP-001 em banco isolado
./run.sh             # Inicia somente em 127.0.0.1:18871
```

Na própria máquina: **http://127.0.0.1:18871**. Para habilitar conscientemente o acesso por outros dispositivos da rede local, execute `TESSITURA_HOST=0.0.0.0 ./run.sh` e acesse **http://IP-DA-MAQUINA:18871**. Para usar outra porta: `TESSITURA_PORT=18872 ./run.sh`.

No Fedora Atomic/Silverblue, execute dentro de uma toolbox que tenha as dependências instaladas. `run.sh` não instala pacotes. Se houver firewall ativo, libere a porta `18871/tcp` apenas para a rede local.

### Operações

```bash
./run.sh build
./run.sh test
./run.sh experiment
./run.sh doctor
./run.sh deps
./run.sh clean    # Remove apenas build/, preserva var/
```

Os dados ficam em `var/tessitura.sqlite3` (excluído do Git). É possível configurar caminho por `TESSITURA_DB`. Faça backup com o banco em repouso ou use a API de backup do SQLite; não copie somente o `.sqlite3` enquanto o servidor estiver escrevendo em WAL.

## EXP-001 — primeira integração científica

A v0.1.2 integra dois recortes reais e versionados: estatísticas municipais do **MapBiomas Brasil Coleção 11** para Bagé em 2023 e observações horárias da estação automática **INMET A827** em janeiro de 2023. Os artefatos oficiais, membros internos, subconjuntos e operações têm SHA-256 e proveniência registrados.

O resultado é deliberadamente `contextual_only`: uma classificação anual agregada ao município e medições horárias de uma estação pontual não são diretamente comparáveis. O experimento registra essa incompatibilidade, uma objeção e a decisão de não inferir associação ou causalidade. Ele não generaliza uma integração completa com as fontes.

`./run.sh experiment` usa `var/exp001/tessitura.sqlite3`, separado do banco padrão, repete a importação para verificar idempotência e grava `report.json` e `dossier.md` em `var/exp001/output/`. O protocolo completo está em [`docs/experiments/EXP-001-protocol.md`](docs/experiments/EXP-001-protocol.md).

## Invariantes

- **Aviso não é evento observado.** Um relatório não é medição instrumental.
- **SHA-256 ≠ validade científica.** O EXP-001 confere os bytes contratados, mas isso não autentica o fenômeno nem valida uma interpretação.
- **Metadados de evidence são imutáveis** (gatilhos no SQLite). Divergência gera novo registro.
- A API remove espaços externos e normaliza SHA-256 para minúsculas antes de calcular o fingerprint; a garantia não depende do formulário web.
- Validade e observação são temporalidades distintas. Datas de calendário impossíveis e intervalos invertidos são rejeitados.
- **`validation_status=not_validated`** por construção. Não há fluxo de aprovação científica nem inteligência artificial nesta versão.
- A persistência local não usa banco, credenciais ou código de MÉTIS, EVIDA ou MORFO.
- Sem autenticação, exponha somente em uma rede local confiável, não publique a porta na internet e não use dados sensíveis.

## API REST

| Método | Rota | Função |
|---|---|---|
| GET | `/api/health` | Estado do servidor |
| GET | `/api/v1/capabilities` | Capacidades reais e ausentes |
| GET | `/api/v1/summary` | Contagens operacionais |
| GET/POST | `/api/v1/evidence` | Cadastro de informações tipadas |
| GET/POST | `/api/v1/investigations` | Perguntas investigáveis |
| GET | `/api/v1/investigations/{id}` | Dossiê e diário |
| POST | `/api/v1/investigations/{id}/links` | Vínculo argumentativo explícito |
| POST | `/api/v1/investigations/{id}/journal` | Pergunta, hipótese, objeção, nota, decisão |
| GET | `/api/v1/audit` | Histórico operacional |

Exemplo seguro, **sem registro de evento físico afirmado**:

```bash
curl -sS http://127.0.0.1:18871/api/health
curl -sS -X POST http://127.0.0.1:18871/api/v1/investigations \
  -H 'Content-Type: application/json' \
  -d '{"title":"Questão inicial","question":"Que evidências permitem reconstruir trajetórias distintas?"}'
```

## Testes e limitações

`ctest` executa três testes sobre bancos temporários. Eles verificam ingestão canônica e idempotente, temporalidade, limite HTTP, imutabilidade, vínculos, diário, auditoria, migração de um banco v0.1.0, hashes históricos e a execução repetida do EXP-001 com rejeição da fixture que transforma ausência em zero. Nada é inserido automaticamente no banco padrão.

Este protótipo possui **servidor HTTP de um cliente por vez**, com timeout de leitura/escrita de 10 segundos e limite de corpo de 64 KiB aplicado pelo parser. A paginação ainda é fixa; não há autenticação nem importação de arquivos. Não é um produto pronto para uso público ou dados sensíveis.

Consulte o [`caderno de fundação`](docs/TESSITURA-FOUNDATION-001_v0.1.0.md), o [`protocolo EXP-001`](docs/experiments/EXP-001-protocol.md) e o [`ADR-003 — Prova vertical`](docs/ADR-003-PRIMEIRA-INTEGRACAO.md).

Licença: GNU GPLv3, texto integral em [`LICENSE`](LICENSE).
