# Azure Tenant Insights (ATI)

> **Un escáner dinámico y escalable de tenant de Azure que genera inventarios Excel estructurados y dos informes HTML (Ejecutivo + Técnico) alineados con el Azure Well-Architected Framework.**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Azure Resource Graph](https://img.shields.io/badge/Azure-Resource%20Graph-0078D4)](https://learn.microsoft.com/es-es/azure/governance/resource-graph/)
[![Licencia: MIT](https://img.shields.io/badge/Licencia-MIT-green)](./LICENSE)

---

## Tabla de Contenidos

- [Descripción General](#descripción-general)
- [¿Qué diferencia a ATI de ARI?](#qué-diferencia-a-ati-de-ari)
- [Requisitos Previos](#requisitos-previos)
- [Instalación](#instalación)
- [Inicio Rápido](#inicio-rápido)
- [Uso](#uso)
- [Referencia de Parámetros](#referencia-de-parámetros)
- [Requisitos de RBAC](#requisitos-de-rbac)
- [Archivos de Salida](#archivos-de-salida)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Archivos de Configuración](#archivos-de-configuración)
- [Entornos de Nube Soportados](#entornos-de-nube-soportados)
- [Limitaciones](#limitaciones)

---

## Descripción General

Azure Tenant Insights (ATI) analiza un tenant de Azure (suscripciones únicas o múltiples, o jerarquía de Management Groups) y produce tres archivos de salida:

| Salida | Audiencia | Contenido |
|---|---|---|
| `*_Inventory.xlsx` | Todos los equipos | Inventario Excel estructurado y multi-hoja, organizado por tipo de recurso |
| `*_Executive.html` | C-Level / Interesados | Puntuación de riesgo, KPIs, recomendaciones estratégicas, señales de modernización |
| `*_Technical.html` | Ingenieros / Arquitectos | Hallazgos por pilar WAF, violaciones de policy, misconfigs, salud, recursos deprecados |

Todos los datos se obtienen **exclusivamente de APIs oficiales de Azure** — Azure Resource Graph, Azure Advisor, Azure Policy Insights, Resource Health y, opcionalmente, Defender for Cloud y Cost Management.

---

## ¿Qué diferencia a ATI de ARI?

[Azure Resource Inventory (ARI)](https://github.com/microsoft/ARI) es una herramienta PowerShell ampliamente utilizada para documentación de Azure. ATI es una solución Python complementaria que aborda brechas clave:

| Dimensión | ARI | ATI |
|---|---|---|
| **Lenguaje** | PowerShell 7+ | Python 3.9+ |
| **Cobertura de tipos de recurso** | Módulos estáticos por tipo (~80+ hardcodeados) | **Dinámica** — todos los tipos descubiertos y capturados automáticamente |
| **Nuevos tipos de recurso** | Actualización manual de módulo requerida | Capturados genéricamente; el enriquecimiento es opcional y aditivo |
| **Informe HTML Ejecutivo** | ❌ | ✅ |
| **Informe HTML Técnico** | ❌ | ✅ |
| **Mapeo de pilares WAF** | ❌ | ✅ vía categorías de Azure Advisor |
| **Detección de misconfiguraciones** | ❌ | ✅ basado en fuentes oficiales |
| **Conformidad con Policy** | Opcional | Siempre recopilado |
| **Detección de recursos deprecados** | ❌ | ✅ basado en anuncios oficiales de retiro |
| **Recursos Azure Arc** | No explícito | Capturados vía tipo `hybridcompute` |

ATI **no reemplaza a ARI** — ambas herramientas pueden usarse juntas. ATI extiende la capa de análisis con informes HTML, alineación WAF y cobertura dinámica de tipos.

---

## Requisitos Previos

- **Python 3.9 o superior**
- **Cuenta Azure** con al menos acceso `Reader` en las suscripciones a analizar
- Uno de los siguientes métodos de autenticación:
  - `az login` (Azure CLI — recomendado para uso local interactivo; sin secretos)
  - Managed Identity (al ejecutar en cómputo Azure)
  - Service Principal vía variables de entorno (escenario avanzado de automatización; consulta `.env.example`)

### Instalar Azure CLI (opcional pero recomendado)

```bash
# Windows (winget)
winget install -e --id Microsoft.AzureCLI

# macOS
brew install azure-cli

# Azure Cloud Shell — preinstalado, no requiere acción
```

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/suellenferreira/azure-tenant-insights.git
cd azure-tenant-insights

# 2. (Recomendado) Crear un entorno virtual
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

---

## Inicio Rápido

```bash
# Autenticarse vía Azure CLI
az login

# Ejecutar ATI contra todas las suscripciones accesibles
python invoke_ati.py

# Ejecutar para un tenant específico
python invoke_ati.py --tenant-id 00000000-0000-0000-0000-000000000000
```

Los archivos de salida se guardan en `./AzureTenantInsights/` por defecto.

---

## Uso

### Ejemplos Básicos

```bash
# Análisis completo del tenant (todas las suscripciones accesibles)
python invoke_ati.py --tenant-id <TENANT-ID>

# Limitar a suscripciones específicas
python invoke_ati.py --tenant-id <TENANT-ID> --subscription-id <SUB-ID-1> <SUB-ID-2>

# Limitar a un Management Group (analiza todas las suscripciones dentro de él)
python invoke_ati.py --tenant-id <TENANT-ID> --management-group <MG-ID>

# Todas las fuentes de datos están ACTIVAS por defecto. Usa --skip-* para excluirlas:
python invoke_ati.py --tenant-id <TENANT-ID> --skip-costs       # sin datos de coste
python invoke_ati.py --tenant-id <TENANT-ID> --skip-defender    # sin Defender for Cloud
python invoke_ati.py --tenant-id <TENANT-ID> --skip-tags        # sin columnas de etiqueta en Excel

# Filtrar por resource group específico
python invoke_ati.py --tenant-id <TENANT-ID> --resource-group rg-produccion rg-staging

# Filtrar por etiqueta (tag)
python invoke_ati.py --tenant-id <TENANT-ID> --tag-key entorno --tag-value produccion

# Opcional: autenticación vía Service Principal para automatización
# Prefiere variables de entorno para evitar secretos en el historial del terminal.
export AZURE_TENANT_ID=<TENANT-ID>
export AZURE_CLIENT_ID=<APP-ID>
export AZURE_CLIENT_SECRET=<SECRET>
python invoke_ati.py

# Directorio de salida y nombre de informe personalizados
python invoke_ati.py --tenant-id <TENANT-ID> \
  --output-dir ./informes \
  --report-name MiEmpresa_Trimestral

# Omitir fuentes de datos para ejecuciones más rápidas
python invoke_ati.py --tenant-id <TENANT-ID> \
  --skip-advisor \
  --skip-policy \
  --no-html

# Modo debug (log detallado)
python invoke_ati.py --tenant-id <TENANT-ID> --debug
```

### Azure Cloud Shell

```bash
# No requiere instalación — Python y az están preinstalados
git clone https://github.com/suellenferreira/azure-tenant-insights.git
cd azure-tenant-insights
pip install -r requirements.txt --quiet
python invoke_ati.py
```

---

## Referencia de Parámetros

### Autenticación

| Parámetro | Descripción |
|---|---|
| `--tenant-id <GUID>` | ID del Tenant de Azure. Opcional — detectado automáticamente del contexto `az login` |
| `--client-id <ID>` | ID de Aplicación del Service Principal |
| `--client-secret <SECRET>` | Secreto del Service Principal. Prefiere `AZURE_CLIENT_SECRET` para automatización y evitar exposición en el historial del terminal |

### Alcance

| Parámetro | Descripción |
|---|---|
| `--subscription-id <ID> [<ID> ...]` | Limitar el análisis a suscripciones específicas |
| `--management-group <ID>` | Analizar todas las suscripciones bajo un Management Group |
| `--resource-group <NOMBRE> [...]` | Limitar a resource groups específicos |
| `--tag-key <CLAVE>` | Filtrar recursos por clave de etiqueta |
| `--tag-value <VALOR>` | Filtrar recursos por valor de etiqueta (requiere `--tag-key`) |

### Fuentes de Datos Opcionales

Todas las fuentes de datos están **activas por defecto**. Usa `--skip-*` para excluirlas:

| Parámetro | Descripción | RBAC Extra Requerido |
|---|---|---|
| `--skip-defender` | Excluir evaluaciones de Defender for Cloud | — |
| `--skip-costs` | Excluir datos de Cost Management | — |
| `--skip-tags` | Excluir columnas de etiquetas del Excel | — |
| `--skip-policy` | Omitir recopilación de conformidad con Azure Policy | — |
| `--skip-advisor` | Omitir recomendaciones de Azure Advisor | — |

### Salida

| Parámetro | Descripción |
|---|---|
| `--output-dir <RUTA>` | Directorio de salida (predeterminado: `./AzureTenantInsights`) |
| `--report-name <NOMBRE>` | Prefijo personalizado para los nombres de archivos de informe |
| `--no-excel` | Omitir generación del inventario Excel |
| `--no-html` | Omitir generación de informes HTML |

### Rendimiento

| Parámetro | Predeterminado | Descripción |
|---|---|---|
| `--throttle-delay <SEGUNDOS>` | `1.0` | Pausa entre consultas al Resource Graph |
| `--cloud <NOMBRE>` | `AzurePublicCloud` | Entorno de nube Azure |

---

## Requisitos de RBAC

| Funcionalidad | Rol Mínimo | Ámbito |
|---|---|---|
| Inventario principal | `Reader` | Suscripción(es) |
| Conformidad con Policy | `Reader` | Suscripción(es) |
| Azure Advisor | `Reader` | Suscripción(es) |
| Resource Health | `Reader` | Suscripción(es) |
| Ámbito Management Group | `Reader` | Management Group |
| Postura de planes Defender | `Reader` | Suscripción(es) |
| Evaluaciones de Defender for Cloud | `Security Reader` | Suscripción(es) |
| Datos de costos | `Cost Management Reader` | Suscripción(es) o Cuenta de Facturación |

> **Principio de Mínimo Privilegio:** ATI es 100% de solo lectura. No realiza ningún cambio en ningún recurso de Azure.

---

## Archivos de Salida

Los informes generados pueden incluir metadatos del tenant, IDs de suscripción, nombres de recursos, costos, hallazgos de seguridad y detalles de configuración. Mantén los archivos generados localmente por defecto y no publiques salidas `AzureTenantInsights/`, `*.xlsx`, `*.html` o `*.log`.

### `*_Inventory.xlsx` — Inventario Excel

| Hoja | Contenido |
|---|---|
| `Overview` | Resumen de KPIs, principales tipos de recurso, Advisor por pilar WAF |
| `Subscriptions` | Una fila por suscripción con conteo de recursos |
| `AllResources` | Tabla plana de TODOS los recursos en todos los tipos |
| `[TipoRecurso]` | Una hoja por tipo de recurso (ej.: `VirtualMachines`) |
| `AdvisorFindings` | Todas las recomendaciones del Advisor con pilar WAF |
| `PolicyCompliance` | Recursos no conformes con policies |
| `ResourceHealth` | Recursos con estado de salud degradado/no disponible |
| `DeprecatedResources` | Recursos correspondientes a anuncios de retiro |
| `MisconfigFindings` | Hallazgos de misconfiguraciones conocidas |
| `SecurityAssessments` | Evaluaciones de Defender for Cloud (omitido con `--skip-defender`) |
| `DefenderCostEstimate` | Costo estimado de los planes Defender a partir del inventario (omitido con `--skip-defender`) |
| `DefenderPosture` | Habilitación de planes Defender por suscripción vía `Microsoft.Security/pricings` (omitido con `--skip-defender`) |
| `DefenderServersCoverage` | Cobertura por recurso de Defender for Servers para VMs / VMSS / Máquinas Arc (omitido con `--skip-defender`) |
| `DefenderCoverageGap` | Unidades facturables desprotegidas y **costo mensual para proteger** por plan (omitido con `--skip-defender`) |
| `Costs` | Costo por resource group/servicio (omitido con `--skip-costs`) |

### `*_Executive.html` — Informe Ejecutivo

Archivo HTML autocontenido. Abrir en cualquier navegador moderno — **no requiere internet** para los datos.

- Banner de nivel de riesgo general
- Tiles de KPI (recursos, suscripciones, hallazgos críticos, deprecados, cobertura de etiquetas)
- Recomendaciones del Advisor por pilar WAF (gráfico de rosca)
- Principales tipos de recurso (gráfico de barras)
- Top 5 hallazgos prioritarios
- Resumen de la postura de planes Defender y **brecha de cobertura** (unidades facturables desprotegidas + costo mensual estimado para proteger) *(si hay datos de Defender)*
- Recomendaciones estratégicas
- Señales de modernización *(etiquetadas como INFERIDO)*

### `*_Technical.html` — Informe Técnico

Archivo HTML autocontenido con navegación lateral.

- Resumen del inventario de recursos
- Hallazgos por pilar WAF (pestañas por pilar)
- Violaciones de conformidad con Policy
- Misconfiguraciones conocidas (con enlace a documentación oficial)
- Evaluaciones de Defender for Cloud *(omitido con `--skip-defender`)*
- **Postura de planes** Defender (planes habilitados/deshabilitados por suscripción) y cobertura por recurso de servidores *(si hay datos de Defender)*
- Tabla de **brecha de cobertura y costo para proteger** (unidades facturables desprotegidas × precio unitario por plan) *(si hay datos de Defender)*
- Eventos de salud de recursos
- Recursos deprecados/en proceso de retiro con enlaces de migración
- Observaciones de Landing Zone *(etiquetadas como INFERIDO)*
- Recursos Azure Arc *(si están presentes)*

---

## Estructura del Proyecto

```
azure-tenant-insights/
│
├── invoke_ati.py                   ← Punto de entrada principal
├── requirements.txt
├── pyproject.toml
├── README.md                       ← Inglés (principal)
├── README.pt-BR.md                 ← Portugués (Brasil)
├── README.es.md                    ← Este archivo (Español)
├── CHANGELOG.md
│
├── config/
│   ├── resource_enrichment.yaml    ← Reglas de promoción de propiedades por tipo
│   ├── deprecated_types.json       ← Anuncios oficiales de retiro de Azure
│   └── misconfiguration_rules.yaml ← Definiciones de reglas de seguridad/configuración
│
├── collectors/                     ← Recopilación de datos de APIs Azure
│   ├── auth.py                     ← Autenticación
│   ├── subscriptions.py            ← Enumeración de suscripciones
│   ├── resource_graph.py           ← Motor principal del Resource Graph (retry/backoff de la CLI)
│   ├── resources.py                ← Recopilación dinámica de recursos
│   ├── advisor.py                  ← Recomendaciones de Azure Advisor
│   ├── policy.py                   ← Estados de conformidad con Policy
│   ├── health.py                   ← Eventos de Resource Health
│   ├── defender.py                 ← Evaluaciones de Defender for Cloud
│   ├── defender_posture.py         ← Postura de planes Defender (Microsoft.Security/pricings)
│   ├── defender_pricing.py         ← Brecha de cobertura + precios en vivo (Azure Retail Prices API)
│   └── costs.py                    ← Datos de Cost Management
│
├── processors/                     ← Enriquecimiento y análisis de datos
│   ├── normalizer.py               ← Utilidades de normalización
│   ├── deprecation.py              ← Detección de recursos deprecados
│   ├── waf_mapper.py               ← Agrupación por pilar WAF
│   ├── misconfig_detector.py       ← Evaluación de reglas de misconfiguraciones
│   └── summary.py                  ← Cálculo de métricas de KPI
│
└── writers/                        ← Generación de salida
    ├── excel_writer.py             ← Constructor del workbook Excel
    ├── html_executive.py           ← Informe HTML Ejecutivo
    └── html_technical.py           ← Informe HTML Técnico
```

---

## Archivos de Configuración

### `config/resource_enrichment.yaml`

Define qué campos anidados de `properties.*` deben promoverse a columnas con nombre por tipo de recurso. Los recursos sin entrada de regla aún se recopilan — el JSON crudo de `properties` se almacena en la hoja `AllResources`.

### `config/deprecated_types.json`

Contiene anuncios de retiro conocidos de Azure. Actualice este archivo cuando se publiquen nuevos anuncios en [Azure Updates](https://azure.microsoft.com/es-es/updates/).

### `config/misconfiguration_rules.yaml`

Define verificaciones de configuración para tipos de recurso específicos. Todas las reglas hacen referencia a documentación oficial de Microsoft.

---

## Entornos de Nube Soportados

| Parámetro | Entorno |
|---|---|
| `AzurePublicCloud` | Azure Global (predeterminado) |
| `AzureUSGovernment` | Azure US Government |
| `AzureChinaCloud` | Azure China (21Vianet) |
| `AzureGermanCloud` | Azure Germany |

---

## Tiempo Estimado de Ejecución

| Tamaño del Tenant | Tiempo Estimado |
|---|---|
| < 500 recursos | ~2 minutos |
| 500–5.000 recursos | ~5–15 minutos |
| 5.000–50.000 recursos | ~15–60 minutos |
| > 50.000 recursos | > 60 minutos (se recomienda programar ejecución nocturna) |

---

## Limitaciones

- **Límite de página del Resource Graph:** 1.000 registros/página. La paginación se gestiona automáticamente.
- **Rate limiting:** El Resource Graph limita las consultas por usuario. Use `--throttle-delay` para ajustar.
- **No todas las propiedades expuestas:** El Resource Graph usa la API no-preview más reciente por tipo. Algunas propiedades solo disponibles en preview pueden no aparecer.
- **Datos de costos requieren RBAC elevado:** Se necesita `Cost Management Reader`.
- **Las estimaciones de costo de Defender son aproximadas:** Los precios unitarios se obtienen en vivo de la Azure Retail Prices API pública (precios de **lista**). Cuando la API no está disponible, se usan los precios de fallback integrados y los informes los etiquetan como fallback offline posiblemente desactualizado. Descuentos EA/MCA/CSP, niveles gratuitos y planes basados en uso (ej.: Cosmos DB) no se reflejan.
- **Gráficos requieren internet:** Chart.js se carga desde CDN. Todas las tablas de datos se muestran sin internet.
- **Solo punto en el tiempo:** ATI produce instantáneas. El análisis de tendencias requiere ejecuciones regulares programadas.
- **Las señales de modernización son INFERIDAS:** Ninguna API oficial de Azure devuelve una puntuación de preparación para IA o modernización. ATI infiere estas señales únicamente a partir de los tipos de recurso detectados.

---

## Licencia

Licencia MIT — consulte [LICENSE](./LICENSE) para más detalles.

> Este proyecto no es un producto oficial de Microsoft. Utiliza únicamente APIs de Azure oficiales y documentadas públicamente.
