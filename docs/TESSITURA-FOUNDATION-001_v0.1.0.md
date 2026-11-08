# TESSITURA — Caderno de fundação científica e arquitetural

**ID:** TESSITURA-FOUNDATION-001
**Versão:** 0.1.0
**Data:** 2026-11-07
**Status:** Protótipo funcional experimental; sem validação científica
**Natureza:** Projeto independente. Não modifica MÉTIS, EVIDA, MORFO ou MPRR.

## 1. Problema científico

Como construir um sistema computacional capaz de apoiar a descoberta, a confrontação e a reconstrução de relações entre processos socioecológicos historicamente constituídos, sem transformar associações em causalidades nem interpretações provisórias em verdades estabelecidas?

A unidade principal é **a investigação**, definida por pergunta, recortes espacial/temporal, vínculos explícitos com fontes e um diário que preserva alternativas e objeções. Não é o índice de resiliência nem o aviso meteorológico.

## 2. Princípios constitutivos

1. **Fontes heterogêneas permanecem heterogêneas.** Aviso meteorológico, medição instrumental, declaração documental, indicador derivado e classificação cartográfica têm naturezas distintas.
2. **Tempo do fenômeno ≠ tempo da observação ≠ tempo da ingestão.** O esquema guarda `valid_start`, `valid_end`, `observed_at`, `observed_start`, `observed_end`, `inserted_at`; não faz arbitragem temporal ou inferência de precedência causal.
3. **Integridade ≠ validade científica.** SHA-256 identifica bytes/metadados, não verifica observação ou interpretação. `source_sha256` nunca é inventado nem recalculado neste piloto.
4. **Ausência ≠ zero.** Campos opcionais permanecem vazios; não completar informações desconhecidas por inferência.
5. **Registro imutável, interpretação revisável.** Evidências, links, diário e auditoria são append-only; novas interpretações devem gerar novos registros, nunca substituir histórias anteriores.
6. **Relação ≠ causa.** `supports`, `contradicts`, `contextualizes` e `questions` indicam vínculo argumentativo, não evidência causal suficiente.
7. **Hipótese ≠ conclusão.** Nenhuma API pode atribuir status de validação científica; toda evidência nasce `not_validated`.
8. **Autonomia.** O núcleo funciona offline, sem EVIDA, MÉTIS, MPRR, INMET, AdaptaBrasil ou MapBiomas.
9. **Local-first e acesso controlado na LAN.** Sem autenticação nesta fase; o script escuta em `127.0.0.1` por padrão e a LAN exige a opção explícita `TESSITURA_HOST=0.0.0.0`. Não publicar na internet nem importar acervos sensíveis nesta versão.
10. **Sempre pronto. Sempre incompleto.** Entregar capacidades verificáveis antes de ampliar modelos e algoritmos.

## 3. Especificação mínima implementada

- `POST /api/v1/evidence`: registro tipado com dados de origem, três temporalidades, referência espacial, contexto e hash opcional. Requisições idênticas produzem mesmo ID (`record_fingerprint` SHA-256 de metadados normalizados).
- `GET /api/v1/evidence`: lista últimos 100 registros, sem promoção automática de estado.
- `POST /api/v1/investigations`: abre investigação com título e pergunta, período e referência espacial opcionais.
- `GET /api/v1/investigations`: lista; `GET /api/v1/investigations/{id}` produz dossiê com vínculos e diário.
- `POST /api/v1/investigations/{id}/links`: associa evidência de maneira explícita, exige tipo e registra justificativa.
- `POST /api/v1/investigations/{id}/journal`: registra `question`, `hypothesis`, `objection`, `decision`, `note`; `request_key` opcional permite idempotência.
- `GET /api/v1/audit`: eventos operacionais; `GET /api/v1/summary` e `GET /api/v1/capabilities`.

**Não implementado:** automação de conectores, importação raster, comparação de séries, motor de descoberta relacional, validação semântica, autoria assinada, autorização multiusuário, mapas e análises estatísticas. O front-end é operacional sobre os endpoints disponíveis, não uma simulação de números.

## 4. Arquitetura

- **C++26**: servidor REST síncrono inicial com Boost.Beast e Boost.JSON; operações implementadas num núcleo único, deliberadamente simples nesta etapa.
- **SQLite WAL**: fonte de verdade local, migrações ordenadas e versionadas com SHA-256 e chaves estrangeiras.
- **OpenSSL**: impressão digital do registro normalizado e verificação do hash da migração, não dos bytes de origem externa.
- **Web**: HTML/CSS/JS sem bundler ou bibliotecas carregadas remotamente, identidade visual inspirada no MORFO: azul-marinho, azul/ciano, superfícies claras e navegação lateral. Não utiliza arquivos de fontes do MORFO.
- **Serviço**: porta `18871` em loopback por padrão, configurável por `TESSITURA_HOST`; timeout de 10 segundos e payload máximo de 64 KiB aplicado durante a leitura HTTP.

A arquitetura inicial é um monólito modularizável, não um conjunto prematuro de microsserviços. Não compartilhar diretamente bancos de dados com MÉTIS ou EVIDA.

## 5. Integrações em avaliação

| Fonte ou sistema | O que poderá oferecer | Condição de integração |
|---|---|---|
| INMET | Avisos e medições | Distinguir previsão, observação e efeito; preservar versão, janela e coordenadas da estação |
| AdaptaBrasil | Índices, modelos, metadados | Homologar códigos, nomenclaturas, metodologia, cenários e anos de referência |
| MapBiomas | Série histórica de uso e cobertura | Preservar coleção, classe, resolução, incerteza, mudança de legenda e unidade espacial |
| EVIDA | Enunciados documentais | Consentimento de publicação, custódia, validação semântica e proveniência do trecho |
| MÉTIS | Resultados de modelos e episódios | Tratar como resultados calculados/hipóteses, não como ocorrência física; citar versão de modelo |
| MPRR | Perguntas e confrontação crítica | Inspiração metodológica opcional, sem acoplamento ou dependência obrigatória |

Até a v0.1.1, nenhuma dessas integrações estava implementada. A v0.1.2 demonstra somente o recorte contratual e offline do EXP-001 com MapBiomas e INMET; isso não equivale a conectores genéricos ou integração institucional com essas fontes.

## 6. Evolução e próximas versões

- **v0.1.1 — Qualidade do núcleo (entregue):** canonicalização antes do fingerprint, validação temporal de calendário, `observed_at` na interface, migrações generalizadas, idempotência do diário por investigação, bind seguro, timeout e limite antecipado do corpo HTTP.
- **v0.1.2 — Prova vertical (entregue):** EXP-001 reproduzível com dois recortes reais, contrato versionado, hashes, incompatibilidade explícita de suportes, dossiê e repetição idempotente. A mudança de sequência está registrada no ADR-003.
- **v0.1.4 — Investigação publicada e tempos explícitos (entregue):** o EXP-001 integra o acervo como execução de uma investigação com pergunta, recorte, protocolo e datas; evidências aceitam instante ou janela observada e o dossiê expõe período referido, observação, vínculo e registro.
- **Próxima decisão:** avaliar as lacunas observadas no EXP-001 antes de escolher entre modularização, proveniência estruturada ou proposições.
- **v0.2.0 — Grafo argumentativo:** introduzir proposições investigativas como entidade de primeira classe e relacionar evidências ao objeto exato que apoiam, contradizem, contextualizam ou questionam.
- **v0.3.0 — Revisão e proveniência:** representar revisão sem apagar história e separar fonte externa, artefato documental, extração e evidência usada na investigação.
- **Futuro**: SQL/PostGIS quando consultas espaciais, volume de dados e multiusuário justificarem. Migração deve preservar a semântica e o histórico original.

## 7. Critérios de aceite da v0.1.0

- Compila com `-std=c++26` e CMake; testes automatizados HTTP e SQLite passam.
- Reiniciar preserva registros; migrar verifica hash do SQL, não executa alteração silenciosa.
- Repetição de ingestão idêntica não duplica evidência; alteração do mesmo `request_key` do diário é rejeitada.
- `UPDATE`/`DELETE` de dados probatórios são bloqueados no banco.
- Aviso não vira ocorrência, hipótese não vira validação, hash não vira prova causal.
- Bind restrito a loopback por padrão; ausência de senha não autoriza exposição na internet.

## 8. Relação com o percurso anterior

Este projeto nasce das discussões sobre historicidade das possibilidades, trajetória dos sistemas, evidências heterogêneas e mecanismos de confrontação científica. O fato de ter surgido nesse percurso não demonstra superioridade científica ou validação. Sua autonomia é condição para experimentar e, se necessário, recusar as hipóteses constitutivas da própria plataforma.
