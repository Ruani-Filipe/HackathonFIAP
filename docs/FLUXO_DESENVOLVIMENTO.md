# Documentação do Fluxo de Desenvolvimento da Solução (MVP) — Threat Modeling via Diagrama

Este documento descreve o **fluxo utilizado no desenvolvimento** do MVP presente neste repositório, incluindo decisões técnicas, iterações, limitações conhecidas e como reproduzir os passos.

---

## 1. Objetivo do MVP

Construir um pipeline que:

1. **Receba uma imagem/PDF** de um diagrama de arquitetura.
2. **Identifique componentes** (nós) e **fluxos** (arestas) automaticamente.
3. **Extraia labels** (nomes) dos componentes via OCR para permitir **tipagem** (ex.: `service`, `database`, `api_gateway`, `user`).
4. **Gere um relatório STRIDE** contendo ameaças e contramedidas.
5. Exiba os resultados em **HTML** e salve artefatos em JSON.

> Observação: este MVP usa heurísticas (baseline) para detecção de componentes/fluxos. A visão “supervisionada” (YOLO etc.) é prevista como evolução.

---

## 2. Estrutura do Projeto (principais arquivos)

- `app/pipeline.py`  
  Pipeline end-to-end: ingestão, detecção, OCR, fluxos, STRIDE e geração de artefatos.

- `app/vision/baseline_detector.py`  
  Detector heurístico de componentes (contornos/retângulos).

- `app/vision/flow_detector.py`  
  Detector heurístico de fluxos (linhas/setas por geometria).

- `app/vision/ocr.py`  
  OCR via Tesseract com pré-processamento e múltiplas tentativas.

- `app/stride.py`  
  Regras STRIDE + inferência de tipo do nó (`infer_node_type`) + filtro de emissão (`_should_emit`).

- `templates/report.html.j2`  
  Template do relatório final em HTML (componentes + ameaças).

- `app/cli_analyze.py`  
  CLI para processar uma imagem por vez.

- `app/cli_batch.py`  
  CLI para rodar em lote e gerar `outputs/batch_summary.json`.

---

## 3. Fluxo do Pipeline (passo a passo)

Abaixo, o que acontece em `app/pipeline.py::analyze_file()`.

### 3.1 Ingestão (imagem ou PDF)
- Se o input for PDF, o pipeline rendeiriza as páginas via **PyMuPDF** (`fitz`) para imagens.
- Se o input for imagem, carrega via **PIL**.
- Sempre salva as imagens usadas em:
  - `outputs/<run_id>/inputs/*.png`

### 3.2 Detecção de componentes (nós)
- Executa `BaselineDetector().detect(...)`.
- Saída: lista de nós com bounding boxes (`bbox`) e `score` (heurístico).

### 3.3 OCR (extração de labels)
A label é a chave para “entender” o tipo do componente. O fluxo de OCR evoluiu em iterações:

#### (A) OCR por bbox com padding
- Para cada nó detectado, faz recorte com **margem/padding** (`pad`) para capturar texto nas bordas.
- Faz pré-processamento forte:
  - upscale (até 3x em recortes pequenos),
  - grayscale,
  - contrast,
  - sharpness,
  - filtros,
  - binarização normal e invertida.

#### (B) Múltiplas tentativas de OCR
- Para cada recorte processado, roda Tesseract com múltiplos `psm`:
  - `--psm 7` (uma linha),
  - `--psm 6` (bloco),
  - `--psm 11` (texto esparso).
- Seleciona automaticamente o **melhor resultado** (texto com maior comprimento após normalização).

#### (C) OCR global (fallback)
- Roda `ocr_full_text()` na página inteira para identificar vocabulário (“service”, “db”, “api”, “gateway”…).
- Se encontrar palavras-chave no texto global, o pipeline permite padding maior no OCR por bbox (ex.: `pad=18`).

#### (D) Filtro de “label boa”
Em `app/pipeline.py` existe `_looks_like_good_label(txt)` para reduzir ruído:
- permite apenas charset seguro,
- verifica mínimo de letras,
- regra de vogais (para descartar lixo),
- exige keyword conhecida ou Title Case com 2+ palavras.

#### (E) Log de progresso no console (para OCR pesado)
Como OCR forte pode demorar, adicionamos logs periódicos:
- `print(f"[OCR] page={p.name} node {i}/{len(page_nodes)} ...")` a cada 25 nós.

### 3.4 Detecção de fluxos (arestas)
- Se não houver override (`flows_override`), usa `BaselineFlowDetector().detect_edges(...)`.
- O detector de fluxo é geométrico: ele conecta nós por linhas/setas.
- Importante: **fluxo não implica label**. É possível ter muitos edges, mas poucos rótulos OCR.

### 3.5 Tipagem de nós (component type inference)
- Em `app/stride.py::infer_node_type(label)` fazemos mapeamento por palavras-chave.
- Tipos suportados (exemplos):
  - `user`, `service`, `server`, `database`, `api_gateway`, `api`, `queue`, `cache`, `storage`, `identity`, `observability`, `cdn`, `waf`, `dns`, `load_balancer`.
- Se não houver sinal suficiente, o tipo fica `component` (genérico).

### 3.6 Geração de ameaças (STRIDE)
- Em `app/stride.py::build_stride_threats(...)`:
  - para cada nó, pega regras pelo tipo (`NODE_RULES`) e aplica filtro `_should_emit(...)`;
  - para edges existe `EDGE_RULES`, mas só emite se houver gatilho (evita gerar STRIDE “inventado”).

**Mudança importante implementada no desenvolvimento:**  
Antes, o sistema emitia todas as letras STRIDE para todos os alvos. Isso foi corrigido para **não inflar o relatório** sem evidência.

### 3.7 Geração do relatório (HTML) + artefatos
O pipeline sempre salva:

- `outputs/<run_id>/artifacts/architecture.json`
- `outputs/<run_id>/artifacts/threats.json`
- `outputs/<run_id>/artifacts/report.html`

O HTML usa `templates/report.html.j2`.

**Mudança importante implementada no desenvolvimento:**
- tabela de “Componentes” não lista `type=component` (genérico).
- tabela de STRIDE não aparece se `threat_items` estiver vazio.

---

## 4. Fluxo de Execução (CLI)

### 4.1 Rodar uma imagem
```bash
python -m app.cli_analyze --input "C:\\...\\inputs\\imagem5.png" --out ".\\outputs"
```

### 4.2 Rodar em lote
```bash
python -m app.cli_batch --input_dir "C:\\...\\inputs" --out ".\\outputs" --limit 4 --shuffle
```

Gera:
- `outputs/batch_summary.json`

---

## 5. Fluxo de Iteração adotado no desenvolvimento (o “como evoluímos”)

1. **Baseline funcional**: detectar caixas e setas, salvar JSON/HTML.
2. **Primeiro OCR**: OCR simples por bbox (`psm 6`).
3. **Ruído alto** → criamos `_looks_like_good_label` para aceitar apenas labels plausíveis.
4. **Muitos “component”** → expandimos `infer_node_type()` e ocultamos `component` no report.
5. **STRIDE inflado** → implementamos `_should_emit` para não gerar categorias sem gatilho.
6. **OCR ainda fraco** → adicionamos:
   - padding no bbox,
   - OCR global,
   - multi-PSM,
   - binarização normal/invertida,
   - sharpness/contraste e upscale maior.
7. **OCR pesado (demora)** → adicionamos logs periódicos no console para visibilidade de progresso.

---

## 6. Limitações conhecidas (MVP)

- O detector de nós/fluxos é heurístico. Diagramas com estilos diferentes podem reduzir a precisão.
- OCR baseado em Tesseract é sensível a:
  - fonte pequena,
  - baixa resolução,
  - texto rotacionado,
  - fundo com gradiente,
  - labels fora do bbox do componente.
- O STRIDE depende de `label/type`: se o OCR falhar, não há gatilho e as ameaças não aparecem (por design, para evitar “inventar”).

---

## 7. Próximos passos recomendados (roadmap técnico)

1. **OCR robusto**: trocar/optar por PaddleOCR ou EasyOCR.
2. **Detecção de texto** (EAST/CRAFT) + associação por proximidade ao nó.
3. **Modelo supervisionado** (YOLOv8) para detecção e classificação de componentes.
4. **Trust boundaries**: detectar áreas (VPC/Subnet/Internet) para gerar ameaças de fluxo (edges) com mais confiança.
5. **KB de vulnerabilidades/contramedidas**: integrar CVE/CWE/CAPEC + mapeamento por tipo de componente.

---

## 8. Como validar rapidamente (checklist)

- Verificar se o pipeline gera:
  - `architecture.json`, `threats.json`, `report.html`
- Conferir no console o log de progresso do OCR:
  - `[OCR] page=... node 25/330 ...`
- Conferir no report se:
  - “Componentes” não lista `component`
  - “Ameaças STRIDE” só aparece quando houver itens

---
