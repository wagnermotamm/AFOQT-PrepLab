# Relatório 4 — Qualidade

Data da geração: 2026-10-13.

Questões gravadas: 5950.
Questões pontuáveis: 5934.
Questões rejeitadas na validação: 0.

## Por subteste

| Subteste | Itens | Pontuáveis |
|---|---:|---:|
| arithmetic-reasoning | 1300 | 1300 |
| aviation-information | 520 | 520 |
| block-counting | 600 | 600 |
| instrument-comprehension | 400 | 400 |
| math-knowledge | 1050 | 1050 |
| physical-science | 518 | 518 |
| reading-comprehension | 160 | 160 |
| self-description | 16 | 0 |
| situational-judgment | 8 | 8 |
| table-reading | 750 | 750 |
| verbal-analogies | 550 | 550 |
| word-knowledge | 78 | 78 |

## Status

- approved_calculation: 4778
- approved_relation: 1148
- familiarization_unscored: 16
- training_rubric: 8

## O que a validação fez

- Impediu enunciado repetido.
- Exigiu uma alternativa correta nos itens pontuáveis.
- Exigiu exatamente cinco alternativas distintas em cada item.
- Rejeitou preenchimentos genéricos como “none of these results” e “not enough information”.
- Gerou os distratores numéricos que faltavam perto do resultado, preservando a unidade.
- Variou os distratores verbais pela relação ou pelo campo lexical de cada enunciado.
- Recalculou o número a partir do enunciado, por outra leitura da mesma fórmula, e rejeitou divergências.
- Conferiu se o fato cobrado na leitura aparece na passagem.
- Embaralhou a posição da alternativa correta com semente estável do enunciado.
- Manteve julgamento situacional fora do status de gabarito oficial.
- Manteve o inventário de autodescrição sem pontuação.

## Lacunas

- Word Knowledge e Situational Judgment ficaram abaixo da meta inicial de 700 e 300 porque não foram inflados com paráfrases quase iguais.
- Reading Comprehension deste lote cobra detalhe explícito. Inferência aberta não entrou, porque a checagem automática não a comprovaria.
- A fórmula exata de cada composto, subteste por subteste, não está no trecho utilizável do DAFMAN 36-2664. O simulado não converte acerto em percentil.
- A página da NASA Glenn não pôde ser lida nesta sessão e não sustenta nenhum item.
- Nenhuma questão foi marcada como oficial ou endossada pela USAF.
- A primeira geração válida tinha 3.589 pontuáveis. O acréscimo até a meta veio de famílias numéricas e espaciais com segunda conta, não de paráfrases verbais.

## Meta sugerida e lote entregue

| Subteste | Meta sugerida | Pontuáveis neste lote |
|---|---:|---:|
| verbal-analogies | 550 | 550 |
| arithmetic-reasoning | 600 | 1300 |
| word-knowledge | 700 | 78 |
| math-knowledge | 600 | 1050 |
| reading-comprehension | 550 | 160 |
| situational-judgment | 300 | 8 |
| physical-science | 400 | 518 |
| table-reading | 350 | 750 |
| instrument-comprehension | 350 | 400 |
| block-counting | 350 | 600 |
| aviation-information | 500 | 520 |
