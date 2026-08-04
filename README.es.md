# Azure Tenant Insights (ATI)

> **Un escáner dinámico y escalable de tenant de Azure que genera inventarios Excel estructurados, dos informes HTML (Ejecutivo + Técnico) y diagramas de arquitectura multipágina (draw.io) alineados con el Azure Well-Architected Framework.**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Azure Resource Graph](https://img.shields.io/badge/Azure-Resource%20Graph-0078D4)](https://learn.microsoft.com/es-es/azure/governance/resource-graph/)
[![Licencia: MIT](https://img.shields.io/badge/Licencia-MIT-green)](./LICENSE)

---

## Tabla de Contenidos

- [Descripción General](#descripción-general)
- [Características Clave](#características-clave)
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
- [Solución de Problemas](#solución-de-problemas)
- [Contribuciones](#contribuciones)

---

## Descripción General

Azure Tenant Insights (ATI) analiza un tenant de Azure (suscripciones únicas o múltiples, o jerarquía de Management Groups) y produce cuatro archivos de salida:

| Salida | Audiencia | Contenido |
|---|---|---|
| `*_Inventory.xlsx` | Todos los equipos | Inventario Excel estructurado y multi-hoja, organizado por tipo de recurso |
| `*_Executive.html` | C-Level / Interesados | Puntuación de riesgo, KPIs, recomendaciones estratégicas, señales de modernización |
| `*_Technical.html` | Ingenieros / Arquitectos | Hallazgos por pilar WAF, violaciones de policy, misconfigs, salud, recursos deprecados |
| `*.drawio` | Arquitectos | Diagrama de arquitectura multipágina — Overview, Organization, Service Model, Business Pillar, Network Topology, Network Detail, Security Posture y Recursos por suscripción — con iconos Azure reales; abra en [draw.io](https://app.diagrams.net) |

Todos los datos se obtienen **exclusivamente de APIs oficiales de Azure** — Azure Resource Graph, Azure Advisor, Azure Policy Insights, Resource Health y, opcionalmente, Defender for Cloud y Cost Management.

---

## Características Clave

- **Cobertura dinámica de tipos de recurso** — todos los tipos del tenant se descubren y capturan automáticamente. Los nuevos tipos de Azure se tratan genéricamente (sin cambios de código); el enriquecimiento por tipo es opcional y aditivo vía `config/resource_enrichment.yaml`.
- **Excel estructurado multi-hoja** — una hoja por tipo de recurso con enriquecimiento declarativo, la tabla plana `AllResources`, una hoja de navegación **Index** (hipervínculos a cada pestaña, con enlaces de retorno por hoja), una columna **Category** (Azure nativo / Híbrido-Arc / Migrate) y una sección **Data Collection Notes**.
- **Informes HTML duales** — Ejecutivo (puntuación de riesgo, KPIs, tarjetas de recomendaciones por prioridad, postura Zero Trust) y Técnico (hallazgos por pilar WAF, policy, misconfigs, salud, recursos deprecados); ambos autocontenidos, con secciones plegables y tablas utilizables sin conexión.
- **Diagrama de arquitectura draw.io** — un `.drawio` multi-página con iconos Azure reales: Overview (KPIs + enlaces entre páginas), **Organization** (árbol Tenant → Management Groups → Subscriptions con conteo de recursos), Service Model, Business Pillar, **Network Topology** (VNets/subnets/peering con detección de peering roto), una página **Network Detail** (recursos dentro de sus subredes: VMs, private endpoints, firewall, gateways, escudo NSG, nodo On-Premises), una página **Security Posture** (tarjetas de riesgo por suscripción + badges de severidad en los recursos) y una página de Recursos por suscripción. Mapa de iconos basado en configuración con fallback genérico, por lo que los nuevos tipos de recurso de Azure se diagraman automáticamente. Omita con `--no-diagram`.
- **Mapeo de pilares WAF** — recomendaciones del Advisor organizadas por pilar del Well-Architected Framework.
- **Detección de misconfiguraciones basada en reglas** — reglas de fuentes oficiales mapeadas a principios Zero Trust.
- **Conformidad de Policy y detección de recursos deprecados** — recursos no conformes y coincidencias con anuncios oficiales de retiro de Azure.
- **Postura de Defender for Cloud** — habilitación de planes por suscripción, cobertura por recurso de servidores y brecha de cobertura con costo para proteger.
- **100% solo lectura** — datos obtenidos exclusivamente de APIs oficiales de Azure (Resource Graph, Advisor, Policy Insights, Resource Health y, opcionalmente, Defender y Cost Management).

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

# Azure Cloud Shell — az CLI ya instalado y con sesión iniciada
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
# Python y az ya vienen listos (az con sesión iniciada) — solo instala las dependencias de Python:
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
| `--no-diagram` | Omitir generación del diagrama de arquitectura draw.io |
| `--network-detail-per-subscription` | Network Detail: una página por suscripción (para tenants muy grandes) |
| `--skip-org` | Omitir recolección de la jerarquía de Management Groups (diagrama Organization) |
| `--no-security-overlay` | Desactivar el overlay de Security Posture en el diagrama (badges + página) |

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
| `Overview` | Resumen de KPIs, principales tipos de recurso, Advisor por pilar WAF, **Resource Origin** (Azure nativo / Híbrido-Arc / Migrate), un resumen de **Service Model** (IaaS/PaaS/SaaS/Hybrid/Supporting) y **Data Collection Notes** |
| `Index` | Hoja de navegación (después de `Overview`) con un hipervínculo a cada pestaña; cada hoja tiene un enlace **↩ Index** de retorno |
| `Classification` | **Taxonomía** de recursos por tipo — Categoría Técnica, Pilar de Negocio, Service Model, Publisher (Microsoft/Third-party) — con pivotes de resumen (config-driven) |
| `Subscriptions` | Una fila por suscripción con conteo de recursos |
| `AllResources` | Tabla plana de TODOS los recursos en todos los tipos, con una columna **Category** (Azure nativo / Híbrido-Arc / Migrate), columnas **Business Pillar** y **Service Model** |
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

> **Nombrado de hojas:** los nombres de las hojas por tipo derivan de los display names configurados; se añade un prefijo corto de namespace **solo** cuando dos providers generarían el mismo nombre (ej.: `Cmp-Virtualmachinetemplates` vs `VMw-Virtualmachinetemplates`). Todos los tipos obtienen su hoja hasta el límite rígido de 255 de Excel; el resto permanece en `AllResources`. Se registra una advertencia por alcance cuando hay muchas hojas de tipo (suscripción ≥ 40, management group ≥ 60, tenant ≥ 75; configurable por variable de entorno).

### `*_Executive.html` — Informe Ejecutivo

Archivo HTML autocontenido. Abrir en cualquier navegador moderno — **no requiere internet** para los datos.

- Banner de nivel de riesgo general
- Tiles de KPI (recursos, suscripciones, hallazgos críticos, deprecados, cobertura de etiquetas)
- Recomendaciones del Advisor por pilar WAF (gráfico de rosca)
- Principales tipos de recurso (gráfico de barras)
- Top hallazgos prioritarios (5, o hasta 10 en entornos grandes)
- Resumen de la postura de planes Defender y **brecha de cobertura** (unidades facturables desprotegidas + costo mensual estimado para proteger) *(si hay datos de Defender)*
- Recomendaciones estratégicas en **tarjetas coloreadas por prioridad**
- Resumen de la postura **Zero Trust** (coloreado por principio, con descripciones)
- Señales de modernización *(etiquetadas como INFERIDO)*
- Secciones plegables con **Expandir Todo / Contraer Todo**; enlace sutil a **Data Collection Notes**

### `*_Technical.html` — Informe Técnico

Archivo HTML autocontenido con navegación lateral.

- Resumen del inventario de recursos; gráfico **Resources by Subscription** etiquetado por el nombre de la suscripción
- Hallazgos por pilar WAF (pestañas por pilar) con **carga progresiva** (30 filas a la vez; las listas grandes remiten al Excel) y **búsqueda por columna**
- Violaciones de conformidad con Policy
- Misconfiguraciones conocidas (con enlace a documentación oficial)
- Evaluaciones de Defender for Cloud *(omitido con `--skip-defender`)*
- **Postura de planes** Defender (planes habilitados/deshabilitados por suscripción, con **búsqueda por columna**) y cobertura por recurso de servidores *(si hay datos de Defender)*
- Tabla de **brecha de cobertura y costo para proteger** (unidades facturables desprotegidas × precio unitario por plan) *(si hay datos de Defender)*
- Eventos de salud de recursos
- Recursos deprecados/en proceso de retiro con enlaces de migración
- Observaciones de Landing Zone *(etiquetadas como INFERIDO)*
- Recursos Azure Arc *(si están presentes)*
- Secciones plegables con **Expandir Todo / Contraer Todo**; enlace sutil a **Data Collection Notes**

### `*_Diagram.drawio` — Diagrama de Arquitectura

Archivo [draw.io](https://app.diagrams.net) multipágina (XML sin comprimir) con iconos Azure reales. Ábralo en la app web/escritorio de draw.io o en la extensión de VS Code. Páginas:

- **Overview** — KPIs por Service Model y Business Pillar, con enlaces a todas las páginas
- **Organization** — árbol Tenant → Management Groups → Subscriptions con conteo de recursos por suscripción
- **Service Model** / **Business Pillar** — tipos de recurso agrupados por IaaS/PaaS/SaaS/… y por pilar de negocio
- **Network Topology** — VNets, subredes y peering (verde = Connected, rojo discontinuo = Disconnected/huérfano), agrupados por suscripción
- **Network Detail** — recursos dentro de sus subredes (VMs, private endpoints, firewall, gateways, escudo NSG, nodo On-Premises)
- **Security Posture** — tarjetas de riesgo por suscripción (cobertura Defender, Zero Trust) y badges de severidad en los recursos de Network Detail *(cuando hay datos de seguridad)*
- **Resources** — una página por suscripción con contenedores de resource group

Los iconos provienen de los stencils Azure 2019 de draw.io, con un fallback genérico para nuevos tipos de recurso. Omita la generación con `--no-diagram`; use `--network-detail-per-subscription` para una página de Network Detail por suscripción y `--no-security-overlay` para desactivar los badges/página de seguridad.

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
│   ├── resource_classification.yaml ← Taxonomía de 3 niveles (Service Model / Business Pillar)
│   ├── deprecated_types.json       ← Anuncios oficiales de retiro de Azure
│   ├── misconfiguration_rules.yaml ← Definiciones de reglas de seguridad/configuración
│   ├── drawio_stencils.yaml        ← Tipo de recurso → icono Azure (diagrama)
│   ├── network_placement.yaml      ← Recurso → resolución de subred (Network Detail)
│   └── security_overlay.yaml       ← Colores de severidad + Zero Trust (diagrama)
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
│   ├── costs.py                    ← Datos de Cost Management
│   └── mgmt_groups.py              ← Jerarquía de Management Groups (diagrama Organization)
│
├── processors/                     ← Enriquecimiento y análisis de datos
│   ├── normalizer.py               ← Utilidades de normalización
│   ├── deprecation.py              ← Detección de recursos deprecados
│   ├── waf_mapper.py               ← Agrupación por pilar WAF
│   ├── misconfig_detector.py       ← Evaluación de reglas de misconfiguraciones
│   ├── classifier.py               ← Taxonomía de clasificación de recursos
│   ├── org_tree.py                 ← Árbol Tenant → MG → Suscripción (diagrama)
│   ├── network_topology.py         ← Grafo VNet/subred/peering (diagrama)
│   ├── network_detail.py           ← Recursos dentro de las subredes (diagrama)
│   ├── security_overlay.py         ← Riesgo por recurso/suscripción (diagrama)
│   └── summary.py                  ← Cálculo de métricas de KPI
│
└── writers/                        ← Generación de salida
    ├── excel_writer.py             ← Constructor del workbook Excel
    ├── html_executive.py           ← Informe HTML Ejecutivo
    ├── html_technical.py           ← Informe HTML Técnico
    └── drawio_writer.py            ← Diagrama de arquitectura multipágina (draw.io)
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

## Solución de Problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `Authentication failed` / no se encuentran suscripciones | Sin sesión, o tenant incorrecto | Ejecute `az login` (o `az login --tenant <ID>`); confirme con `az account show` |
| `AuthorizationFailed` / `403` en el log para algunos datos | Falta de RBAC en una suscripción | Garantice al menos `Reader`; añada `Security Reader` (Defender) / `Cost Management Reader` (costos), o use `--skip-defender` / `--skip-costs` |
| Escaneo lento o log `429 TooManyRequests` | Throttling del Resource Graph | Aumente `--throttle-delay` (ej.: `2.0`); reduzca el alcance con `--subscription-id` o `--management-group` |
| Ejecución prolongada | El alcance por defecto son **todas** las suscripciones del tenant | Reduzca el alcance, o pase `-y` para omitir la confirmación |
| Se cuelga en el prompt "Custom Report Name" en CI | Sin terminal interactivo (TTY) | Pase `--report-name <NOMBRE>` o `-y` (ambos omiten el prompt) |
| Los gráficos no se muestran | Sin conexión / CDN bloqueada | Las tablas funcionan sin conexión; los gráficos necesitan `cdn.jsdelivr.net` |
| Logs HTTP muy detallados | `--debug` habilitado | Omita `--debug`; el SDK de Azure oculta los tokens como `REDACTED` |

> **La autenticación con Service Principal** lee `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` del **entorno**. Expórtelas (o simplemente use `az login`) — un archivo `.env` no se carga automáticamente.

---

## Contribuciones

1. Haga un fork del repositorio
2. Cree una rama de feature: `git checkout -b feature/mi-mejora`
3. Realice los cambios y pruébelos en una suscripción Azure real
4. Abra un Pull Request con una descripción clara

Para añadir una nueva regla de misconfiguración, edite `config/misconfiguration_rules.yaml` y proporcione:
- Un `id` único
- Una referencia a la documentación oficial de Microsoft en `documentation_url`
- El `condition_path` y el `expected_value` exactos, basados en la documentación oficial de la API

---

## Licencia

Licencia MIT — consulte [LICENSE](./LICENSE) para más detalles.

> Este proyecto no es un producto oficial de Microsoft. Utiliza únicamente APIs de Azure oficiales y documentadas públicamente.
