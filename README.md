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

### 1.3 Base para evolução: dataset → anotação → treino supervisionado
O MVP já separa claramente a etapa de **detecção** (visão) do resto do pipeline. Para evoluir:
- substituir `BaselineDetector` por um detector treinado (YOLOv8/Detectron2);
- criar dataset e anotação;
- treinar e plugar no pipeline.

---

## 2) Estrutura do repositório

- `app/cli_analyze.py`  
  CLI para rodar análise de um arquivo e gerar outputs.

- `app/pipeline.py`  
  Orquestra o pipeline:
  - PDF → imagens
  - detecção de componentes
  - geração STRIDE
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
- Se existem N nós, normalmente existem ~`6 * N` itens (S/T/R/I/D/E por nó).

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

## 6) Como isso se conecta com o “projeto final” (próximos passos)

Para atender a proposta completa (modelo supervisionado + vulnerabilidades por componente):

1) **Dataset de diagramas**  
   - coletar imagens de arquitetura (draw.io, slides, docs, artigos, etc.)
   - normalizar resolução e formatos

2) **Anotação**  
   - ferramentas: Label Studio / Roboflow / CVAT
   - classes sugeridas: `user`, `server`, `database`, `api`, `queue`, `storage`, `external_system`, etc.

3) **Treino supervisionado**
   - sugestão: YOLOv8 (ultralytics)
   - exportar o modelo e carregar no pipeline no lugar do `BaselineDetector`

4) **Extração de fluxos**
   - detectar setas/linhas (ou anotar fluxos também)
   - gerar `edges` automaticamente

5) **Vulnerabilidades e contramedidas específicas**
   - mapear tipo de componente → CWE/OWASP ASVS/OWASP Top 10/CAPEC
   - enriquecer o `threats.json` e o `report.html` com referências

---

## 7) Troubleshooting

### “Não detectou componentes”
Normal no baseline. A heurística depende muito do estilo do diagrama (caixas, bordas, contraste).  
Evolução recomendada: modelo supervisionado.

### “Caracteres acentuados estranhos no HTML”
O projeto força UTF-8 ao gravar o `report.html`. Se você ainda ver problema:
- confirme que está abrindo o arquivo atualizado em `outputs/<run_id>/artifacts/report.html`
- confirme que seu navegador/editor está abrindo em UTF-8

---

## 8) Licença
Defina a licença que preferir (MIT, Apache-2.0 etc.) antes de publicar no GitHub.
