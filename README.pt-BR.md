# Azure Tenant Insights (ATI)

> **Um scanner dinâmico e escalável de tenant Azure que gera inventários Excel estruturados e relatórios HTML duplos (Executivo + Técnico) alinhados com o Azure Well-Architected Framework.**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Azure Resource Graph](https://img.shields.io/badge/Azure-Resource%20Graph-0078D4)](https://learn.microsoft.com/pt-br/azure/governance/resource-graph/)
[![Licença: MIT](https://img.shields.io/badge/Licença-MIT-green)](./LICENSE)

---

## Índice

- [Visão Geral](#visão-geral)
- [O que diferencia o ATI do ARI](#o-que-diferencia-o-ati-do-ari)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Início Rápido](#início-rápido)
- [Uso](#uso)
- [Referência de Parâmetros](#referência-de-parâmetros)
- [Requisitos de RBAC](#requisitos-de-rbac)
- [Arquivos de Saída](#arquivos-de-saída)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Arquivos de Configuração](#arquivos-de-configuração)
- [Ambientes de Nuvem Suportados](#ambientes-de-nuvem-suportados)
- [Limitações](#limitações)

---

## Visão Geral

O Azure Tenant Insights (ATI) realiza o scan de um tenant Azure (assinaturas únicas ou múltiplas, ou hierarquia de Management Groups) e produz três arquivos de saída:

| Saída | Público-Alvo | Conteúdo |
|---|---|---|
| `*_Inventory.xlsx` | Todas as equipes | Inventário Excel estruturado e multi-abas, organizado por tipo de recurso |
| `*_Executive.html` | C-Level / Stakeholders | Pontuação de risco, KPIs, recomendações estratégicas, sinais de modernização |
| `*_Technical.html` | Engenheiros / Arquitetos | Findings por pilar WAF, violações de policy, misconfigs, saúde, recursos deprecados |

Todos os dados são obtidos **exclusivamente de APIs oficiais do Azure** — Azure Resource Graph, Azure Advisor, Azure Policy Insights, Resource Health e, opcionalmente, Defender for Cloud e Cost Management.

---

## O que diferencia o ATI do ARI

O [Azure Resource Inventory (ARI)](https://github.com/microsoft/ARI) é uma ferramenta PowerShell amplamente utilizada para documentação Azure. O ATI é uma solução complementar em Python que endereça lacunas importantes:

| Dimensão | ARI | ATI |
|---|---|---|
| **Linguagem** | PowerShell 7+ | Python 3.9+ |
| **Cobertura de tipos de recurso** | Módulos estáticos por tipo (~80+ hardcoded) | **Dinâmica** — todos os tipos descobertos e capturados automaticamente |
| **Novos tipos de recurso** | Atualização manual de módulo necessária | Capturados genericamente; enriquecimento é opcional e aditivo |
| **Relatório HTML Executivo** | ❌ | ✅ |
| **Relatório HTML Técnico** | ❌ | ✅ |
| **Mapeamento para pilares WAF** | ❌ | ✅ via categorias do Azure Advisor |
| **Detecção de misconfiguração** | ❌ | ✅ baseado em fontes oficiais |
| **Conformidade com Policy** | Opcional | Sempre coletado |
| **Detecção de recursos deprecados** | ❌ | ✅ baseado em anúncios oficiais de aposentadoria |
| **Recursos Azure Arc** | Não explícito | Capturados via tipo `hybridcompute` |

O ATI **não substitui o ARI** — ambas as ferramentas podem ser utilizadas em conjunto. O ATI estende a camada de análise com relatórios HTML, alinhamento WAF e cobertura dinâmica de tipos.

---

## Pré-requisitos

- **Python 3.9 ou superior**
- **Conta Azure** com pelo menos acesso `Reader` nas assinaturas a serem escaneadas
- Um dos seguintes métodos de autenticação:
  - `az login` (Azure CLI — recomendado para uso local interativo; sem secrets)
  - Managed Identity (ao executar em computação Azure)
  - Service Principal via variáveis de ambiente (cenário avançado de automação; veja `.env.example`)

### Instalar Azure CLI (opcional, mas recomendado)

```bash
# Windows (winget)
winget install -e --id Microsoft.AzureCLI

# macOS
brew install azure-cli

# Azure Cloud Shell — pré-instalado, nenhuma ação necessária
```

---

## Instalação

```bash
# 1. Clonar o repositório
git clone https://github.com/suellenferreira/azure-tenant-insights.git
cd azure-tenant-insights

# 2. (Recomendado) Criar um ambiente virtual
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Instalar dependências
pip install -r requirements.txt
```

---

## Início Rápido

```bash
# Autenticar via Azure CLI
az login

# Executar o ATI contra todas as assinaturas acessíveis
python invoke_ati.py

# Executar para um tenant específico
python invoke_ati.py --tenant-id 00000000-0000-0000-0000-000000000000
```

Os arquivos de saída são salvos em `./AzureTenantInsights/` por padrão.

---

## Uso

### Exemplos Básicos

```bash
# Scan completo do tenant (todas as assinaturas acessíveis)
python invoke_ati.py --tenant-id <TENANT-ID>

# Restringir a assinaturas específicas
python invoke_ati.py --tenant-id <TENANT-ID> --subscription-id <SUB-ID-1> <SUB-ID-2>

# Restringir a um Management Group (escaneia todas as assinaturas abaixo dele)
python invoke_ati.py --tenant-id <TENANT-ID> --management-group <MG-ID>

# Todas as fontes de dados estão ACTIVAS por padrão. Use --skip-* para excluir:
python invoke_ati.py --tenant-id <TENANT-ID> --skip-costs       # sem dados de custo
python invoke_ati.py --tenant-id <TENANT-ID> --skip-defender    # sem Defender for Cloud
python invoke_ati.py --tenant-id <TENANT-ID> --skip-tags        # sem colunas de tags no Excel

# Filtrar por resource group específico
python invoke_ati.py --tenant-id <TENANT-ID> --resource-group rg-producao rg-staging

# Filtrar por tag
python invoke_ati.py --tenant-id <TENANT-ID> --tag-key ambiente --tag-value producao

# Opcional: autenticação via Service Principal para automação
# Prefira variáveis de ambiente para evitar secrets no histórico do terminal.
export AZURE_TENANT_ID=<TENANT-ID>
export AZURE_CLIENT_ID=<APP-ID>
export AZURE_CLIENT_SECRET=<SECRET>
python invoke_ati.py

# Diretório de saída e nome de relatório personalizados
python invoke_ati.py --tenant-id <TENANT-ID> \
  --output-dir ./relatorios \
  --report-name MinhaEmpresa_Trimestral

# Pular fontes de dados específicas para execuções mais rápidas
python invoke_ati.py --tenant-id <TENANT-ID> \
  --skip-advisor \
  --skip-policy \
  --no-html

# Modo debug (log detalhado)
python invoke_ati.py --tenant-id <TENANT-ID> --debug
```

### Azure Cloud Shell

```bash
# Não requer instalação — Python e az estão pré-instalados
git clone https://github.com/suellenferreira/azure-tenant-insights.git
cd azure-tenant-insights
pip install -r requirements.txt --quiet
python invoke_ati.py
```

---

## Referência de Parâmetros

### Autenticação

| Parâmetro | Descrição |
|---|---|
| `--tenant-id <GUID>` | ID do Tenant Azure. Opcional — detectado automaticamente do contexto `az login` |
| `--client-id <ID>` | ID do Aplicativo do Service Principal |
| `--client-secret <SECRET>` | Secret do Service Principal. Prefira `AZURE_CLIENT_SECRET` em automações para evitar exposição no histórico do terminal |

### Escopo

| Parâmetro | Descrição |
|---|---|
| `--subscription-id <ID> [<ID> ...]` | Restringir o scan a assinaturas específicas |
| `--management-group <ID>` | Escanear todas as assinaturas sob um Management Group |
| `--resource-group <NOME> [...]` | Restringir a resource groups específicos |
| `--tag-key <CHAVE>` | Filtrar recursos por chave de tag |
| `--tag-value <VALOR>` | Filtrar recursos por valor de tag (requer `--tag-key`) |

### Fontes de Dados Opcionais

| Parâmetro | Descrição | RBAC Extra Necessário | Padrão |
|---|---|---|---|
| `--skip-defender` | Pular coleta do Defender for Cloud | — | Incluído (incluir por padrão) |
| `--skip-costs` | Pular dados do Cost Management | — | Incluído (incluir por padrão) |
| `--skip-tags` | Pular coluna de tags no Excel | — | Incluído (incluir por padrão) |
| `--skip-policy` | Pular coleta de conformidade com Azure Policy | — | Incluído |
| `--skip-advisor` | Pular recomendações do Azure Advisor | — | Incluído |

### Saída

| Parâmetro | Descrição |
|---|---|
| `--output-dir <CAMINHO>` | Diretório de saída (padrão: `./AzureTenantInsights`) |
| `--report-name <NOME>` | Prefixo personalizado para os nomes dos arquivos de relatório |
| `--no-excel` | Pular geração do inventário Excel |
| `--no-html` | Pular geração dos relatórios HTML |

### Performance

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `--throttle-delay <SEGUNDOS>` | `1.0` | Atraso entre consultas ao Resource Graph |
| `--cloud <NOME>` | `AzurePublicCloud` | Ambiente de nuvem Azure |

---

## Requisitos de RBAC

| Funcionalidade | Role Mínimo | Escopo |
|---|---|---|
| Inventário principal | `Reader` | Assinatura(s) |
| Conformidade com Policy | `Reader` | Assinatura(s) |
| Azure Advisor | `Reader` | Assinatura(s) |
| Resource Health | `Reader` | Assinatura(s) |
| Escopo Management Group | `Reader` | Management Group |
| Postura de planos Defender | `Reader` | Assinatura(s) |
| Avaliações do Defender for Cloud | `Security Reader` | Assinatura(s) |
| Dados de custo | `Cost Management Reader` | Assinatura(s) ou Conta de Faturamento |

> **Princípio do Menor Privilégio:** O ATI é 100% somente leitura. Nenhuma alteração é feita em nenhum recurso Azure.

---

## Arquivos de Saída

Os relatórios gerados podem incluir metadados do tenant, IDs de assinatura, nomes de recursos, custos, findings de segurança e detalhes de configuração. Mantenha os arquivos gerados localmente por padrão e não publique saídas `AzureTenantInsights/`, `*.xlsx`, `*.html` ou `*.log`.

### `*_Inventory.xlsx` — Inventário Excel

| Aba | Conteúdo |
|---|---|
| `Overview` | Resumo de KPIs, principais tipos de recurso, Advisor por pilar WAF |
| `Subscriptions` | Uma linha por assinatura com contagem de recursos |
| `AllResources` | Tabela plana de TODOS os recursos em todos os tipos |
| `[TipoRecurso]` | Uma aba por tipo de recurso (ex.: `VirtualMachines`) |
| `AdvisorFindings` | Todas as recomendações do Advisor com pilar WAF |
| `PolicyCompliance` | Recursos não conformes com policies |
| `ResourceHealth` | Recursos com estado de saúde degradado/indisponível |
| `DeprecatedResources` | Recursos correspondentes a anúncios de aposentadoria |
| `MisconfigFindings` | Findings de misconfigurações conhecidas |
| `SecurityAssessments` | Avaliações do Defender for Cloud (omitido com `--skip-defender`) |
| `DefenderCostEstimate` | Custo estimado dos planos Defender a partir do inventário (omitido com `--skip-defender`) |
| `DefenderPosture` | Habilitação de planos Defender por assinatura via `Microsoft.Security/pricings` (omitido com `--skip-defender`) |
| `DefenderServersCoverage` | Cobertura por recurso do Defender for Servers para VMs / VMSS / Máquinas Arc (omitido com `--skip-defender`) |
| `DefenderCoverageGap` | Unidades faturáveis desprotegidas e **custo mensal para proteger** por plano (omitido com `--skip-defender`) |
| `Costs` | Custo por resource group/serviço (omitido com `--skip-costs`) |

### `*_Executive.html` — Relatório Executivo

Arquivo HTML autocontido. Abrir em qualquer navegador moderno — **sem necessidade de internet** para os dados.

- Banner de nível de risco geral
- Tiles de KPI (recursos, assinaturas, findings críticos, deprecados, cobertura de tags)
- Recomendações do Advisor por pilar WAF (gráfico de rosca)
- Principais tipos de recurso (gráfico de barras)
- Top 5 findings prioritários
- Resumo da postura de planos Defender e **gap de cobertura** (unidades faturáveis desprotegidas + custo mensal estimado para proteger) *(se houver dados do Defender)*
- Recomendações estratégicas
- Sinais de modernização *(rotulados como INFERIDO)*

### `*_Technical.html` — Relatório Técnico

Arquivo HTML autocontido com navegação lateral.

- Resumo do inventário de recursos
- Findings por pilar WAF (abas por pilar)
- Violações de conformidade com Policy
- Misconfigurations conhecidas (com link para documentação oficial)
- Avaliações do Defender for Cloud *(omitido com `--skip-defender`)*
- **Postura de planos** Defender (planos ligados/desligados por assinatura) e cobertura por recurso de servidores *(se houver dados do Defender)*
- Tabela de **gap de cobertura e custo para proteger** (unidades faturáveis desprotegidas × preço unitário por plano) *(se houver dados do Defender)*
- Eventos de saúde dos recursos
- Recursos deprecados/em processo de aposentadoria com links de migração
- Observações de Landing Zone *(rotuladas como INFERIDO)*
- Recursos Azure Arc *(se presentes)*

---

## Estrutura do Projeto

```
azure-tenant-insights/
│
├── invoke_ati.py                   ← Ponto de entrada principal
├── requirements.txt
├── pyproject.toml
├── README.md                       ← Inglês (principal)
├── README.pt-BR.md                 ← Este arquivo (Português BR)
├── README.es.md                    ← Espanhol
├── CHANGELOG.md
│
├── config/
│   ├── resource_enrichment.yaml    ← Regras de promoção de propriedades por tipo
│   ├── deprecated_types.json       ← Anúncios oficiais de aposentadoria Azure
│   └── misconfiguration_rules.yaml ← Definições de regras de segurança/configuração
│
├── collectors/                     ← Coleta de dados das APIs Azure
│   ├── auth.py                     ← Autenticação
│   ├── subscriptions.py            ← Enumeração de assinaturas
│   ├── resource_graph.py           ← Motor principal do Resource Graph (retry/backoff da CLI)
│   ├── resources.py                ← Coleta dinâmica de recursos
│   ├── advisor.py                  ← Recomendações do Azure Advisor
│   ├── policy.py                   ← Estados de conformidade com Policy
│   ├── health.py                   ← Eventos de Resource Health
│   ├── defender.py                 ← Avaliações do Defender for Cloud
│   ├── defender_posture.py         ← Postura de planos Defender (Microsoft.Security/pricings)
│   ├── defender_pricing.py         ← Gap de cobertura + preços ao vivo (Azure Retail Prices API)
│   └── costs.py                    ← Dados do Cost Management
│
├── processors/                     ← Enriquecimento e análise de dados
│   ├── normalizer.py               ← Utilitários de normalização
│   ├── deprecation.py              ← Detecção de recursos deprecados
│   ├── waf_mapper.py               ← Agrupamento por pilar WAF
│   ├── misconfig_detector.py       ← Avaliação de regras de misconfigurações
│   └── summary.py                  ← Cálculo de métricas de KPI
│
└── writers/                        ← Geração de saída
    ├── excel_writer.py             ← Construtor do workbook Excel
    ├── html_executive.py           ← Relatório HTML Executivo
    └── html_technical.py           ← Relatório HTML Técnico
```

---

## Arquivos de Configuração

### `config/resource_enrichment.yaml`

Define quais campos aninhados de `properties.*` devem ser promovidos para colunas nomeadas por tipo de recurso. Recursos sem entrada de regra ainda são coletados — o JSON bruto de `properties` é armazenado na aba `AllResources`.

### `config/deprecated_types.json`

Contém anúncios conhecidos de aposentadoria Azure. Atualize este arquivo quando novos anúncios forem publicados em [Azure Updates](https://azure.microsoft.com/pt-br/updates/).

### `config/misconfiguration_rules.yaml`

Define verificações de configuração para tipos de recurso específicos. Todas as regras referenciam documentação oficial da Microsoft.

---

## Ambientes de Nuvem Suportados

| Flag | Ambiente |
|---|---|
| `AzurePublicCloud` | Azure Global (padrão) |
| `AzureUSGovernment` | Azure US Government |
| `AzureChinaCloud` | Azure China (21Vianet) |
| `AzureGermanCloud` | Azure Germany |

---

## Tempo Estimado de Execução

| Tamanho do Tenant | Tempo Estimado |
|---|---|
| < 500 recursos | ~2 minutos |
| 500–5.000 recursos | ~5–15 minutos |
| 5.000–50.000 recursos | ~15–60 minutos |
| > 50.000 recursos | > 60 minutos (recomenda-se agendar para execução noturna) |

---

## Limitações

- **Limite de página do Resource Graph:** 1.000 registros/página. A paginação é tratada automaticamente.
- **Rate limiting:** O Resource Graph limita consultas por usuário. Use `--throttle-delay` para ajustar.
- **Nem todas as propriedades expostas:** O Resource Graph usa a API mais recente não-preview por tipo. Algumas propriedades disponíveis apenas em preview podem não aparecer.
- **Dados de custo requerem RBAC elevado:** `Cost Management Reader` é necessário.
- **Estimativas de custo do Defender são aproximadas:** Os preços unitários são obtidos ao vivo da Azure Retail Prices API pública (preços de **lista**). Quando a API está indisponível, são usados os preços de fallback internos e os relatórios os rotulam como fallback offline possivelmente desatualizado. Descontos EA/MCA/CSP, camadas gratuitas e planos baseados em uso (ex.: Cosmos DB) não são refletidos.
- **Gráficos requerem internet:** O Chart.js é carregado via CDN. Todas as tabelas de dados são exibidas sem internet.
- **Apenas ponto no tempo:** O ATI produz snapshots. A análise de tendências requer execuções regulares agendadas.
- **Sinais de modernização são INFERIDOS:** Nenhuma API oficial do Azure retorna uma pontuação de prontidão para IA ou modernização. O ATI infere esses sinais apenas a partir dos tipos de recurso detectados.

---

## Licença

Licença MIT — consulte [LICENSE](./LICENSE) para detalhes.

> Este projeto não é um produto oficial da Microsoft. Utiliza apenas APIs Azure oficiais e documentadas publicamente.
