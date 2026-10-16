# Como usar o banco de treino do AFOQT

Este material é um treino original. Não é endossado pela USAF, não reproduz a prova e não converte acerto em percentil oficial.

Há dois simulados na mesma pasta, e eles não misturam questões:

- `index.html` usa só o panfleto antigo, a forma anterior à estrutura de 2026.
- `treino.html` usa o banco original descrito nos relatórios.

## Abrir no navegador

O banco é um arquivo JSON. O navegador não o carrega se a página for aberta por `file://`.

1. Entre na pasta `AFOQT Simulator`.
2. Dê um duplo clique em `iniciar.bat`, ou rode `python -m http.server 8765` nessa pasta.
3. Abra `http://127.0.0.1:8765/treino.html`.

## O que dá para fazer

- Escolher simulado completo, por área ou a trilha verbal e quantitativa.
- Ver o cronômetro de cada seção. O intervalo de 15 minutos pode ser pulado.
- Clicar uma palavra sublinhada para ler o sentido em português, sem marcar a alternativa.
- Receber na hora se a resposta pontuável ficou certa ou errada.
- Sair de uma pergunta e voltar por meio do menu. O menu marca certa, errada, em branco ou, no inventário, apenas marcada.
- Ver, no fim, o percentual de cada seção, um índice verbal de treino e um índice quantitativo de treino.

O inventário de autodescrição não tem resposta certa. O julgamento situacional mostra uma rubrica de treino, não um gabarito oficial.

## Arquivos

| Caminho | Conteúdo |
|---|---|
| `banco/afoqt.sqlite` | Fontes, assuntos, questões, alternativas, glossário, validação e simulados |
| `banco/schema.sql` | Esquema |
| `banco/generate_bank.py` | Gerador com a segunda conta das questões numéricas |
| `banco/export/questions.json` | Banco usado pela página |
| `banco/export/questions.csv` | Enunciado, resposta e fonte, sem as figuras |
| `banco/export/blueprints.json` | Simulados e tempos |
| `banco/export/manifest.json` | Contagem e aviso |
| `relatorios/01-catalogo-fontes.md` | Fontes e direitos de uso |
| `relatorios/02-matriz-conteudos.md` | Os 12 subtestes e o rastreio |
| `relatorios/03-plano-cobertura.md` | Metas e o que foi entregue |
| `relatorios/04-qualidade.md` | Aprovadas, rejeitadas e lacunas |

Para gerar o banco de novo:

```text
python "banco\generate_bank.py"
```

O script apaga e recria `banco/afoqt.sqlite` e a pasta `banco/export`. Não altere o gerador para colar questão de prova, de panfleto ou de curso comercial.
