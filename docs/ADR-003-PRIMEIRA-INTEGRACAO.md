# ADR-003 — Prova vertical antes da modularização e das proposições

**Status:** aceita para a v0.1.2  
**Data:** 2026-11-07

## Contexto

A v0.1.1 tornou o núcleo mais preciso, mas não demonstrou integração de fontes científicas heterogêneas. A diretriz `TESSITURA-DIR-001` propôs reordenar o roadmap: executar primeiro uma investigação pequena com dados reais e deixar que falhas observadas orientem novas entidades e módulos.

O ADR-002 previa modularização na v0.1.2 e proposições na v0.2.0. Esta decisão altera explicitamente a sequência; não sobrescreve silenciosamente aquele compromisso.

## Decisão

1. A v0.1.2 entrega o `EXP-001`, com MapBiomas Coleção 11 e INMET A827 no recorte Bagé/2023.
2. A integração é um adaptador Python por contrato, offline após a preparação dos subconjuntos. O núcleo C++ permanece autônomo e os sistemas de origem não são modificados.
3. O contrato JSON Schema e os arquivos de registro preservam dimensões que o modelo v0.1.1 ainda não representa: artefato, versão, suporte espacial, granularidade, qualidade e transformação.
4. A API existente registra somente as duas representações que cabem honestamente no modelo: classificação anual municipal e agregado derivado de observações horárias. Ambas apenas `contextualize` a investigação.
5. A compatibilidade é uma operação explícita com três saídas possíveis. Para o EXP-001, o resultado esperado é `contextual_only`, porque município/ponto e ano/hora não são suportes equivalentes.
6. A execução ocorre duas vezes sobre o mesmo banco e deve produzir zero novos registros lógicos na repetição.
7. Não criar nesta versão tabelas genéricas de artefato, operação, proposição, processo ou trajetória. As lacunas observadas serão entradas para nova deliberação.

## Evidências que sustentam a decisão

- Os artefatos oficiais foram obtidos e seus hashes integrais registrados.
- O modo `prepare` regenera subconjuntos com hashes idênticos a partir dos ZIPs oficiais.
- O contrato rejeita uma fixture que converte ausência em zero.
- O dossiê precisa distinguir um agregado derivado de medições dos registros horários que o originaram.
- O modelo atual não possui intervalo de observação, suporte espacial estruturado nem entidade de transformação; essas lacunas são agora demonstradas, não presumidas.

## Consequências

- A modularização ampla passa a ser candidata posterior à v0.1.2 e deverá usar o adaptador real como caso de teste.
- Proposições permanecem hipótese útil, mas o EXP-001 não exige implementá-las: a pergunta, dois vínculos contextuais, a objeção e a decisão preservam corretamente este caso.
- Artefatos e operações de proveniência mostraram necessidade concreta, porém ainda não justificam uma migração antes de avaliar o dossiê e a manutenção do contrato externo.
- O termo “integração demonstrada” fica restrito a este recorte, estas versões, estes hashes e estas operações. Não implica integração genérica com MapBiomas ou INMET.

## Critério para a próxima decisão

Uma próxima migração deverá responder a pelo menos uma falha observada no EXP-001: representação insuficiente de artefatos/transformações, necessidade de intervalo de observação, consulta de suporte espacial ou ambiguidade argumentativa que não possa ser preservada no diário e nos vínculos atuais.
