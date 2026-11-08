# ADR-002 — Qualidade do núcleo antes do grafo argumentativo

**Status:** Aceita para a v0.1.1  
**Data:** 2026-11-07

## Contexto

A v0.1.0 demonstrou que a investigação pode ser a unidade central do TESSITURA, mas deixou garantias importantes dependentes da interface, uma única migração fixa no código e três descrições conflitantes sobre exposição de rede. Antes de introduzir proposições, conectores ou automação, o núcleo precisa tornar precisos os contratos que já afirma oferecer.

## Decisões

1. O servidor e `run.sh` escutam em `127.0.0.1` por padrão. A exposição na LAN exige `TESSITURA_HOST=0.0.0.0` e continua sem autenticação.
2. Todo texto recebido pela API perde espaços externos antes da validação. Hashes SHA-256 são normalizados para minúsculas antes do fingerprint e da persistência.
3. Datas ISO-8601 são validadas como datas reais de calendário. Intervalos exigem a mesma granularidade, são comparados como instantes e `observed_at` passa a existir no formulário web.
4. Migrações são descobertas em `db/migrations`, ordenadas pelo prefixo de três dígitos, verificadas por SHA-256 e aplicadas individualmente em transações. Alteração ou remoção de uma migração registrada interrompe a abertura do banco.
5. `request_key` do diário é única no escopo de uma investigação. A migração `002_journal_request_scope.sql` preserva os registros existentes e troca a restrição global por `UNIQUE(investigation_id, request_key)`.
6. O parser HTTP limita o corpo a 64 KiB antes da materialização completa e as operações de leitura e escrita expiram após 10 segundos. O servidor permanece deliberadamente sequencial nesta etapa.
7. Append-only continua significando proteção contra alterações pelas operações normais do banco; não será descrito como ledger inviolável, autenticação criptográfica ou validade científica.

## Consequências

- Formulário e clientes diretos passam a produzir a mesma identidade canônica para entradas equivalentes. Fingerprints gravados antes da v0.1.1 não são recalculados, pois evidências históricas permanecem imutáveis.
- O campo `datetime-local` é convertido pelo navegador para UTC antes do envio; clientes de API devem informar timestamp com `Z` ou offset explícito.
- Um cliente lento deixa de bloquear indefinidamente o único fluxo de atendimento, mas concorrência continua fora do escopo desta versão.
- A migração 002 reconstrói somente a tabela `journal`, dentro de uma transação, e recria seus gatilhos append-only.
- A próxima mudança estrutural deve separar o monólito por responsabilidades sem alterar comportamento; depois disso, proposições investigativas podem se tornar entidades de primeira classe.

## Não decidido

- Não há ainda `source_time`, incerteza temporal, revisão de evidências, assinatura de auditoria ou autenticação.
- Evidências continuam vinculadas diretamente à investigação até que o contrato de proposições seja especificado em ADR próprio.
- Nenhum conector, modelo de linguagem, banco espacial ou mecanismo automático de inferência é introduzido por esta decisão.
