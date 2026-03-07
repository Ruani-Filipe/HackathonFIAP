# Threat Modeling MVP (STRIDE) — Leitor de Diagramas de Arquitetura

Este repositório contém um **MVP funcional** que:
1) recebe um **diagrama de arquitetura** (PDF ou imagem),  
2) tenta **identificar componentes** automaticamente (versão baseline/heurística),  
3) gera **ameaças e contramedidas** com base na metodologia **STRIDE**,  
4) exporta artefatos rastreáveis (`architecture.json`, `threats.json`, `report.html`) em `outputs/`.

> Importante: a detecção de componentes nesta versão é **heurística** (baseline). O objetivo do MVP é provar o **pipeline fim-a-fim** e deixar pronto o encaixe de um modelo supervisionado (ex.: YOLO) treinado com dataset anotado.

---

## 1) O que o projeto entrega (objetivos atendidos)

### 1.1 Interpretar diagrama e identificar componentes
- Entrada: PDF/imagem.
- Saída: uma lista de **nós** (componentes) com **bounding boxes (bbox)** e metadados.
- Implementação: `app/vision/baseline_detector.py` (detector simples por contornos/retângulos).

### 1.2 Gerar Relatório de Modelagem de Ameaças (STRIDE)
- Para cada componente identificado, o sistema gera ameaças/contramedidas em STRIDE.
- Implementação: `app/stride.py` + relatório HTML via Jinja (`templates/report.html.j2`).

### 1.3 Aderência rápida (sem treinar modelo agora)
Para o deadline, focamos em melhorias que aumentam a aderência sem exigir treino supervisionado:
- **OCR no bbox** para preencher `label` dos nós com texto do próprio diagrama (explicabilidade);
- **extração heurística de fluxos** (HoughLinesP + proximidade) para preencher `edges`;
- **referências OWASP/CWE** anexadas às ameaças STRIDE (campo `references` + coluna no report).

(Como evolução futura, o `BaselineDetector` pode ser substituído por um detector treinado, ex.: YOLOv8.)

---

## 2) Estrutura do repositório

- `app/cli_analyze.py`  
  CLI para rodar análise de um arquivo e gerar outputs.

- `app/pipeline.py`  
  Orquestra o pipeline:
  - PDF → imagens
  - detecção de componentes
  - OCR (labels por bbox + fallback global)
  - detecção de fluxos (heurística)
  - geração STRIDE (com filtro para não inflar)
  - escrita dos artefatos

- `app/vision/`
  - `baseline_detector.py`: detecção heurística (caixas/retângulos)
  - `io.py`: utilitários de leitura/conversão de imagem

- `app/stride.py`  
  Regras STRIDE (ameaças + contramedidas base).

- `app/reporting.py` + `templates/report.html.j2`  
  Renderização do relatório HTML (Jinja2).

- `outputs/`  
  Pasta gerada automaticamente (ignorável no Git). Contém os artefatos por execução.

---

## 3) Instalação

### Requisitos
- Python 3.11+ (recomendado)
- Windows (o projeto também pode funcionar em Linux/Mac, mas foi testado aqui no Windows)

### Instalar dependências
No terminal (PowerShell ou CMD), dentro da pasta do projeto:

```powershell
python -m pip install -r requirements.txt
```

---

## 4) Como executar (CLI)

Exemplo com PDF:

```powershell
python -m app.cli_analyze --input "C:\caminho\arquivo.pdf" --out ".\outputs"
```

Exemplo com imagem:

```powershell
python -m app.cli_analyze --input "C:\caminho\diagrama.png" --out ".\outputs"
```

O comando imprime um `run_id` e os caminhos dos artefatos gerados.

---

## 5) O que sai em `outputs/` (como validar que funcionou)

Cada execução cria uma pasta:

```
outputs/<run_id>/
  inputs/
    page_1.png
    page_2.png
    ...
  artifacts/
    architecture.json
    threats.json
    report.html
```

### 5.1 `inputs/` (evidência do que foi processado)
Se o input for PDF, cada página vira uma imagem `page_N.png`.  
Isso comprova “o que o sistema viu”.

### 5.2 `architecture.json` (valida a interpretação do diagrama)
Contém:
- `nodes`: componentes detectados (id, bbox, página, score, etc.)
- `edges`: fluxos (no MVP são opcionais; podem vir vazios)

Validação rápida:
- `nodes` deve existir (pode ser > 0 dependendo do diagrama)
- cada nó tem `bbox` e `page` para rastreabilidade.

### 5.3 `threats.json` (valida STRIDE aplicado)
Contém `items` com ameaças/contramedidas e vínculo ao alvo (`target_id`).

Validação rápida:
- O MVP **não** emite STRIDE “automático” para tudo: só gera ameaças quando há **gatilhos plausíveis** (label/tipo).
- Em diagramas onde o OCR não extrai palavras-chave suficientes, `threats.json` pode vir com poucos (ou zero) itens — por design, para evitar “inventar” ameaças.

### 5.4 `report.html` (entregável final)
Relatório legível com:
- tabela de componentes detectados
- tabela de ameaças STRIDE + contramedidas

Abrir no Windows:
```powershell
Start-Process ".\outputs\<run_id>\artifacts\report.html"
```

#### Encoding (UTF-8)
O `report.html` é gravado forçando UTF-8 no `app/pipeline.py` para evitar problemas de encoding no Windows.

---

## 6) O que mostrar no vídeo (roteiro rápido)

1) **Rodar a análise** (CLI):
```powershell
python -m app.cli_analyze --input "C:\\Users\\devru\\OneDrive\\Área de Trabalho\\evidencia1.png" --out ".\\outputs"
```

2) **Abrir o report** e explicar as 3 partes:
- **Componentes (nós)**: cada linha é um elemento detectado no diagrama.
  - `BBox`: onde está o elemento na imagem (prova/rastreabilidade).
  - `Label`: texto extraído via OCR (quando disponível).
- **Fluxos (edges)**: conexões inferidas entre nós (heurístico).
- **Ameaças STRIDE**: ameaças por nó/fluxo + contramedidas.
  - **Referências**: OWASP/CWE anexadas para dar base técnica.

3) **Mostrar os artefatos** em `outputs/<run_id>/artifacts/`:
- `architecture.json`: nós + fluxos com bbox.
- `threats.json`: STRIDE com `references`.
- `report.html`: relatório final.

## 7) Documentação do fluxo de desenvolvimento
- Detalhamento completo do pipeline, iterações e limitações: `docs/FLUXO_DESENVOLVIMENTO.md`

## 8) Evoluções futuras (se houver tempo depois)
- Classificação real de componentes (user/api/database etc.) via modelo supervisionado.
- Detecção robusta de setas/direção (arrowheads) para melhorar `edges`.
- OCR mais robusto (ex.: PaddleOCR/EasyOCR + detecção de texto CRAFT/EAST).
- Enriquecimento de KB (CAPEC/ASVS) e severidade/priorização.

---

## 9) Troubleshooting

### “Não detectou componentes”
Normal no baseline. A heurística depende muito do estilo do diagrama (caixas, bordas, contraste).  
Evolução recomendada: modelo supervisionado.

### “Caracteres acentuados estranhos no HTML”
O projeto força UTF-8 ao gravar o `report.html`. Se você ainda ver problema:
- confirme que está abrindo o arquivo atualizado em `outputs/<run_id>/artifacts/report.html`
- confirme que seu navegador/editor está abrindo em UTF-8

---

## 10) Licença
Defina a licença que preferir (MIT, Apache-2.0 etc.) antes de publicar no GitHub.
