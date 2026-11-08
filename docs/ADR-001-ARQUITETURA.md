# ADR-001 — Fundação local-first, monólito científico e contratos explícitos

**Status:** Aceita somente para o protótipo v0.1.0
**Data:** 2026-11-07

## Contexto

Temos outros projetos operacionais independentes (MÉTIS, EVIDA, MORFO, TRAMA). O novo laboratório não pode converter a necessidade de investigação temporal em acoplamento prematuro a arquiteturas e bases existentes.

## Decisões

1. Iniciar como **novo projeto**: `tessitura`, sem modificar repositórios existentes.
2. Implementar núcleo em **C++26** e uma **API local** com um só processo, sem credenciais e restrita a loopback.
3. Persistir metadados investigativos em **SQLite WAL**. Não armazenar rasters/coleções inteiras no SQLite, nem fingir que ele substitui PostGIS em análises espaciais em produção.
4. Usar Boost.Beast e Boost.JSON para evitar framework de aplicações e empacotadores front-end; OpenSSL apenas para hashes operacionais.
5. Usar **interface visual própria**, inspirada na paleta, no contraste e nos elementos de navegação do MORFO. Não compartilhar bibliotecas de UI, recursos de autenticação, fontes ou assets privados.
6. Preservar fonte, tipo, enunciado, validade temporal, referência espacial e proveniência. Não transformar automaticamente `not_validated` em estado de aprovação.
7. Registro científico e vínculos são append-only. Correções futuras precisam de mecanismo explícito de revisão, não UPDATE silencioso.
8. Contratos de ingestão devem ser discutidos antes de conectar INMET, AdaptaBrasil, EVIDA ou MapBiomas.

## Consequências / dívida consciente

- SQLite preserva simplicidade e facilidade de transporte no laptop, mas faltam consultas geográficas robustas, versionamento distribuído e suporte a múltiplos autores.
- Servidor HTTP síncrono evita complexidade inicial, mas limita concorrência; qualquer exposição externa exige autenticação, rate limits, revisões de segurança e possivelmente substituição do servidor.
- Identidade do operador é rótulo não autenticado: **não representa assinatura científica**.
- A migração `001_foundation.sql` tem hash de integridade verificado na inicialização. Modificações devem gerar nova migração, não alterar a 001 aplicada.
- Limite de 100 registros nas listas atuais; faltam filtros, paginação, ordenação controlada e índices adequados a uso extensivo.
- Temporalidades estão presentes no esquema, mas ainda faltam semânticas de evento, fuso, granularidade, calendário, censura e incerteza da data.
- A decisão por C++26 não obriga a incorporar todo processamento numérico ou geoespacial a C++; adaptadores Python e PostGIS futuros podem operar por contratos.

## Condição de evolução

Uma nova tecnologia só será adicionada depois que uma investigação controlada demonstrar a necessidade. Requisitos de desempenho exigem medições; requisitos de interpretação exigem critérios científicos.
