# Service Desk Analytics

[![CI](https://github.com/CelsoKaiqueSil/service-desk-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/CelsoKaiqueSil/service-desk-analytics/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Pandas](https://img.shields.io/badge/Pandas-análise-150458?logo=pandas&logoColor=white)](src/service_desk_analytics/pipeline.py)
[![SLA](https://img.shields.io/badge/KPIs-SLA%20%7C%20P90-1769D2)](src/service_desk_analytics/pipeline.py)
[![Excel](https://img.shields.io/badge/Excel-dashboard-217346?logo=microsoftexcel&logoColor=white)](src/service_desk_analytics/pipeline.py)
[![Data](https://img.shields.io/badge/dados-100%25%20sintéticos-14804A)](data/tickets.csv)

Projeto de Business Intelligence para consolidar o fluxo de atendimento de um
Service Desk em indicadores operacionais claros, auditáveis e reproduzíveis.

## Indicadores

- chamados abertos, resolvidos, encerrados e backlog;
- percentual de cumprimento de SLA;
- primeira resposta e solução em horas;
- média, mediana e percentil 90;
- volume por categoria, urgência e responsável;
- metodologia registrada junto ao relatório.

## Por que média, mediana e P90?

A média pode ser distorcida por poucos chamados muito longos. A mediana representa
o comportamento típico e o P90 mostra o limite abaixo do qual 90% dos atendimentos
foram concluídos. O uso conjunto evita conclusões simplistas.

## Arquitetura

```mermaid
flowchart LR
    A["Service Desk"] --> B["Coleta"]
    B --> C["Reconciliação"]
    C --> D["Regras de status"]
    D --> E["SLA e tempos"]
    E --> F["Segmentações"]
    F --> G["Excel executivo"]
```

## Executar

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
service-desk-report --input data/tickets.csv --output output/service_desk.xlsx
pytest -q
```

## Qualidade e privacidade

- tickets, pessoas, categorias e datas do exemplo são fictícios;
- identificadores permanecem como texto para preservar zeros e formatos;
- campos ausentes não são inferidos como cumprimento ou violação de SLA;
- as regras de cálculo ficam disponíveis na página `Metodologia`;
- nenhuma credencial ou resposta real de API é incluída.

## Contexto profissional

O estudo representa a consolidação de chamados e indicadores para reuniões de
acompanhamento, priorização de backlog e melhoria contínua do atendimento.
