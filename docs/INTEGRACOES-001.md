# TESSITURA — Mapa de integrações

**Estado:** descritivo da versão 0.1.4  
**Princípio:** interoperabilidade por contrato sem compartilhamento de bancos ou dependência operacional obrigatória.

## 1. O que conta como integração

O TESSITURA distingue quatro situações:

1. **Referência manual:** uma pessoa registra uma fonte como evidência não validada. Isso não demonstra integração.
2. **Adaptador contratual offline:** um processo versionado transforma um artefato identificado em um registro que satisfaz um contrato TESSITURA.
3. **Conector genérico:** um componente consulta diferentes recortes de uma fonte segundo uma interface estável. Ainda não existe.
4. **Integração institucional ou sincronização:** envolve credenciais, acordos, atualização e governança entre sistemas. Ainda não existe.

O percurso pretendido é:

`fonte externa → aquisição explícita → adaptador externo → contrato versionado → evidência → vínculo justificado com investigação`

O adaptador não modifica a origem. O núcleo C++ não lê bancos de outros sistemas. O registro preserva identidade, proveniência, semântica, temporalidade, suporte espacial, qualidade e advertências.

## 2. Matriz atual

| Sistema | Estado | O que existe | O que não existe |
|---|---|---|---|
| INMET | Demonstrado em recorte único | EXP-001, estação A827, janeiro de 2023, adaptador offline e contrato `tessitura.integration-record.v1` | conector online, outras estações/períodos arbitrários, sincronização |
| AdaptaBrasil | Planejado | requisitos conceituais registrados | adaptador, contrato homologado, dados incorporados, método de aquisição definido |
| EVIDA | Planejado | limite de autonomia e requisitos de custódia registrados | leitura de banco, API contratada, pacote exportado, dado incorporado |

## 3. INMET — integração demonstrada

O EXP-001 realiza a seguinte sequência:

1. obtenção explícita do ZIP anual oficial de 2023;
2. conferência do SHA-256 do ZIP e do CSV interno da estação A827;
3. seleção das observações de janeiro de 2023;
4. tratamento de `""`, `9999` e `Null` como ausentes, nunca como zero;
5. agregação diária de precipitação e temperatura pelo adaptador `exp001-adapter/1.0.0`;
6. conferência do subconjunto e validação do contrato de integração;
7. registro pela API como indicador derivado não validado;
8. vínculo `contextualizes` com uma investigação explícita.

Essa demonstração não autoriza afirmar que o TESSITURA está genericamente integrado ao INMET. Ela vale apenas para os artefatos, hashes, parâmetros e operações documentados no EXP-001.

## 4. AdaptaBrasil — contrato ainda necessário

Antes de implementar um adaptador, uma decisão deverá fixar:

- forma oficial de aquisição e termos de uso;
- códigos e nomenclaturas de indicadores;
- versão do modelo, cenário e ano de referência;
- unidade, resolução e suporte espacial;
- incertezas, limites metodológicos e revisões;
- regra de identidade e equivalência operacional.

Até essa decisão, uma referência ao AdaptaBrasil pode ser registrada manualmente como evidência não validada, mas isso não será chamado de integração.

## 5. EVIDA — exportação sem acoplamento

O TESSITURA não deve ler diretamente o banco do EVIDA. Uma integração futura deverá ocorrer por pacote exportado ou API contratada e preservar:

- consentimento e permissão de publicação;
- identidade e versão do documento;
- trecho exato e método de extração;
- custódia, autoria e condições de acesso;
- estado de validação semântica;
- advertências sobre alcance e interpretação.

O EVIDA continua autônomo. O TESSITURA recebe somente o que tiver sido deliberadamente exportado segundo um contrato verificável.

## 6. Próximas decisões

1. Deliberar se o segundo adaptador deve testar índices/modelos do AdaptaBrasil ou enunciados documentais exportados pelo EVIDA.
2. Definir o contrato específico antes de escrever o conector.
3. Executar um recorte pequeno, reproduzível e verificável.
4. Só então avaliar generalização, atualização e interface de seleção.
