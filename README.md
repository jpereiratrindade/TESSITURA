# TESSITURA — Laboratório de trajetórias e relações socioecológicas

**v0.1.0 · C++26 · SQLite WAL · web local · inspirado visualmente no MORFO**

> Faça simples. Depois deixe mais leve. Sempre pronto. Sempre incompleto.

Protótipo funcional, independente, centrado em **situações investigáveis**. Registra perguntas, evidências tipadas com proveniência e tempo, relações explicitamente justificadas e um diário de hipóteses/objeções. Não faz inferência nem confirma causalidade.

## Fedora 44 — início rápido

Instale as dependências no **host Fedora 44 ou na toolbox**, conforme onde pretende compilar/executar:

```bash
sudo dnf install -y gcc-c++ cmake ninja-build boost-devel sqlite-devel openssl-devel python3
```

Depois:

```bash
cd /home/jpereiratrindade/dev/cpp/tessitura
./run.sh test        # Compila e executa teste local ponta a ponta
./run.sh             # Inicia em 0.0.0.0:18871 para acesso pela rede local
```

Na própria máquina: **http://127.0.0.1:18871**. Em outro dispositivo da rede: **http://IP-DA-MAQUINA:18871**. Para usar outra porta: `TESSITURA_PORT=18872 ./run.sh`. Para restringir novamente ao acesso local: `TESSITURA_HOST=127.0.0.1 ./run.sh`.

No Fedora Atomic/Silverblue, execute dentro de uma toolbox que tenha as dependências instaladas. `run.sh` não instala pacotes. Se houver firewall ativo, libere a porta `18871/tcp` apenas para a rede local.

### Operações

```bash
./run.sh build
./run.sh test
./run.sh doctor
./run.sh deps
./run.sh clean    # Remove apenas build/, preserva var/
```

Os dados ficam em `var/tessitura.sqlite3` (excluído do Git). É possível configurar caminho por `TESSITURA_DB`. Faça backup com o banco em repouso ou use a API de backup do SQLite; não copie somente o `.sqlite3` enquanto o servidor estiver escrevendo em WAL.

## Invariantes

- **Aviso não é evento observado.** Um relatório não é medição instrumental.
- **SHA-256 de fonte registrado ≠ bytes externos auditados.** Esta versão não transfere nem confere arquivos de fonte.
- **Metadados de evidence são imutáveis** (gatilhos no SQLite). Divergência gera novo registro.
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

`ctest` executa teste HTTP sobre banco temporário e verifica ingestão idempotente, imutabilidade, vínculos, diário, auditoria e declarações de capacidade. Nada é inserido automaticamente no banco de produção.

Este protótipo possui **servidor HTTP síncrono de um cliente por vez**, paginação ainda fixa, formulário sem autenticação, validação sintática básica de datas e sem importação de arquivos. Não é um produto pronto para uso público ou dados sensíveis.

Consulte: [`docs/TESSITURA-FOUNDATION-001_v0.1.0.md`](docs/TESSITURA-FOUNDATION-001_v0.1.0.md).

Licença: GNU GPLv3, texto integral em [`LICENSE`](LICENSE).
