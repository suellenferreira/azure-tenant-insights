# Azure Tenant Insights (ATI)

> **Un analyseur dynamique et évolutif de tenants Azure qui génère des inventaires Excel structurés, deux rapports HTML (Exécutif + Technique) et des diagrammes d’architecture multipages (draw.io) alignés sur Azure Well-Architected Framework.**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Azure Resource Graph](https://img.shields.io/badge/Azure-Resource%20Graph-0078D4)](https://learn.microsoft.com/en-us/azure/governance/resource-graph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](./LICENSE)

**Langues :** [English](README.md) · Français · [Português (Brasil)](README.pt-BR.md) · [Español](README.es.md)

---

## Table des matières

- [Vue d’ensemble](#vue-densemble)
- [Pourquoi et quand exécuter ATI](#pourquoi-et-quand-exécuter-ati)
- [Exemples de résultats](#exemples-de-résultats)
- [Fonctionnalités principales](#fonctionnalités-principales)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Démarrage rapide](#démarrage-rapide)
- [Traitement des données client et clause de non-responsabilité relative à l’utilisation](#traitement-des-données-client-et-clause-de-non-responsabilité-relative-à-lutilisation)
- [Utilisation](#utilisation)
- [Référence des paramètres](#référence-des-paramètres)
- [Exigences RBAC](#exigences-rbac)
- [Fichiers de sortie](#fichiers-de-sortie)
- [Structure du projet](#structure-du-projet)
- [Fichiers de configuration](#fichiers-de-configuration)
- [Environnements cloud pris en charge](#environnements-cloud-pris-en-charge)
- [Limitations](#limitations)
- [Résolution des problèmes](#résolution-des-problèmes)
- [Contribution](#contribution)

---

## Vue d’ensemble

Azure Tenant Insights (ATI) analyse un tenant Azure (un ou plusieurs abonnements, ou une hiérarchie de groupes d’administration) et produit quatre fichiers de sortie :

| Sortie | Public | Contenu |
|---|---|---|
| `*_Inventory.xlsx` | Toutes les équipes | Inventaire Excel structuré et multifeuille, organisé par type de ressource, comprenant une vue d’ensemble des signaux de configuration régionale et multizone |
| `*_Executive.html` | Direction / Parties prenantes | Score de risque, KPI, recommandations stratégiques, signaux de modernisation et observations sur la posture de résilience |
| `*_Technical.html` | Ingénieurs / Architectes | Constatations par pilier WAF, violations de stratégies, erreurs de configuration, état d’intégrité, ressources dépréciées et analyse détaillée de la résilience régionale et multizone |
| `*.drawio` | Architectes | Diagramme d’architecture multipages — Vue d’ensemble, Organisation, Modèle de service, Pilier métier, Topologie réseau, Détail du réseau, Posture de sécurité et Ressources par abonnement — avec de véritables icônes Azure ; à ouvrir dans [draw.io](https://app.diagrams.net) |

Toutes les données proviennent **exclusivement des API Azure officielles** — Azure Resource Graph, Azure Advisor, Azure Policy Insights, Resource Health et, facultativement, Defender for Cloud et Cost Management.

La vue de la posture de résilience reflète uniquement les propriétés de ressources observées dans l’inventaire Azure Resource Graph. Elle comprend :
- La distribution régionale (les régions qui contiennent des ressources)
- Les signaux de configuration multizone (les ressources qui exposent des propriétés de zone)

Elle ne comprend PAS la validation de la protection des sauvegardes au niveau de la charge de travail, l’intégrité opérationnelle des sauvegardes ni les détails d’architecture propres aux services.

---

## Pourquoi et quand exécuter ATI

Les environnements Azure contiennent souvent les informations nécessaires à une évaluation, mais ces informations sont réparties entre les abonnements, les types de ressources, les régions, les stratégies, les recommandations Advisor, Defender for Cloud et les données de coût.

ATI rassemble ces signaux dans une évaluation en lecture seule qui aide les équipes à passer de :

> « Que possédons-nous ? »

à :

> « Que devons-nous comprendre, valider et examiner ensuite ? »

ATI aide à répondre à des questions telles que :

- Quelles ressources et quels services Azure sont actuellement déployés ?
- Où se trouvent les principaux signaux de sécurité, de gouvernance, d’intégrité et de conformité ?
- Comment l’environnement est-il réparti entre les abonnements, les régions, les modèles de service et les domaines métier ?
- Quelles fonctionnalités cloud natives, de données, d’IA, d’intégration ou de plateforme sont déjà présentes ?
- Où peuvent se trouver des opportunités de modernisation, d’optimisation ou de gouvernance ?
- Quels éléments probants les architectes, les équipes de sécurité et les équipes de compte devraient-ils approfondir ?

### 🧭 Quand ATI est utile

ATI est utile lorsqu’une équipe a besoin d’une base de référence fondée sur des éléments probants pour :

- La découverte d’un client ou d’un tenant ;
- Les évaluations d’adoption du cloud et de zone d’atterrissage ;
- La planification de la modernisation et de la transformation des applications ;
- Les revues de posture de sécurité et de gouvernance ;
- Les revues d’architecture et d’empreinte régionale ;
- La planification de la consolidation ou de la migration des abonnements ;
- Les présentations à la direction, les QBR et les ateliers techniques ;
- Les instantanés périodiques permettant de comparer l’évolution d’un environnement Azure dans le temps.

ATI peut être exécuté sur un seul abonnement pour une évaluation ciblée ou sur plusieurs abonnements lorsqu’une vue plus large au niveau du tenant est nécessaire. Pour une première exécution, il est recommandé de limiter l’analyse à un abonnement.

### 🔎 De l’inventaire aux informations exploitables

| Sans ATI* (processus de référence basé sur le portail/CLI) | Avec ATI |
|---|---|
| Les informations sur les ressources sont réparties entre les abonnements et les services Azure | Un inventaire consolidé est généré pour l’étendue sélectionnée |
| Les éléments probants sont recueillis sur plusieurs pages du portail, requêtes CLI et exportations | Les signaux sont regroupés dans un ensemble cohérent de rapports et de vues |
| Les discussions sur la modernisation nécessitent généralement une corrélation supplémentaire entre les sources et les équipes | Les signaux initiaux de modernisation sont étayés par les modèles de ressources Azure observés |
| La production de résultats adaptés à différents publics (direction, technique, architecture) nécessite généralement une préparation supplémentaire | Les vues exécutive, technique, Excel et d’architecture sont générées ensemble |
| La répétabilité dépend de la reproduction manuelle de l’étendue, des requêtes et des étapes d’exportation | L’évaluation peut être répétée à l’aide du même processus en lecture seule |

> **\*** Les outils d’évaluation spécialisés (notamment Azure Migrate pour les scénarios de migration) peuvent fournir une analyse approfondie propre à chaque scénario. Cette comparaison reflète un processus générique centré sur le portail/CLI sans ATI.

### ✨ Ce qui distingue ATI

ATI ne remplace pas Azure Portal, Azure Resource Graph, Defender for Cloud, Azure Advisor ni les outils d’évaluation spécialisés. Son objectif est de fournir une vue consolidée et reproductible de ces sources et de rendre les éléments probants recueillis utiles à différents publics.

- **Les dirigeants** obtiennent une vue concise des risques, de la posture, de l’empreinte et des signaux d’opportunité.
- **Les architectes et les ingénieurs** obtiennent des éléments probants au niveau des ressources, des correspondances avec les référentiels et des diagrammes d’architecture.
- **Les équipes de sécurité et de gouvernance** obtiennent des constatations liées aux contrôles Azure et aux recommandations officielles de Microsoft.
- **Les analystes et les équipes de compte** obtiennent une base de référence structurée pour la découverte, la priorisation et les échanges de suivi.

### 🛡️ Pourquoi les résultats sont fiables

ATI est conçu pour rendre claires les limites de son évaluation :

- **Lecture seule par conception :** ATI ne crée, ne modifie ni ne supprime aucune ressource Azure.
- **Sources Azure officielles :** les données sont collectées à partir des API et services Azure officiels, notamment Resource Graph, Advisor, Policy, Resource Health, Defender for Cloud et Cost Management lorsqu’ils sont activés et accessibles.
- **Résultats fondés sur des éléments probants :** les rapports présentent les nombres de ressources, les constatations, les classifications, les références aux référentiels et les éléments probants associés plutôt que des conclusions inexpliquées.
- **Signaux inférés explicites :** les indicateurs de modernisation et de préparation sont signalés comme des signaux inférés à partir des modèles de ressources observés.
- **Résultats tenant compte de l’étendue :** les constatations s’appliquent uniquement aux abonnements, groupes d’administration, groupes de ressources et sources de données inclus dans l’analyse.

ATI ne certifie pas la conformité, ne remplace pas un audit de sécurité formel et ne garantit pas la préparation à la modernisation. Les résultats visent à établir une base initiale d’éléments probants pour la validation, les discussions d’architecture et la priorisation.

Pour la méthodologie technique, les sources de données, les correspondances avec les référentiels, les options de configuration et les limitations, consultez [DOCUMENTATION.md](./DOCUMENTATION.md).

---

## Exemples de résultats

> Toutes les captures d’écran ci-dessous utilisent des **données synthétiques et fictives** (un exemple de tenant « Contoso ») à titre d’illustration uniquement — aucune information réelle de tenant, d’abonnement ou de ressource.

### Rapport HTML exécutif

Rapport complet avec une barre de navigation latérale, des KPI, des graphiques et la section Cloud Modernization Signals & Opportunity :

![Rapport exécutif — page complète](docs/images/executive-full.png)

Cloud Modernization Signals & Opportunity — graphiques As-Is, jauge de préparation et cartes d’opportunité :

![Exécutif — Modernization Signals & Opportunity](docs/images/executive-modernization.png)

### Rapport HTML technique

Navigation dans la barre latérale gauche avec la section Modernization Signals (As-Is + Opportunities) :

![Rapport technique — barre latérale + Modernization](docs/images/technical-modernization.png)

### Inventaire Excel

Tableau de bord Overview — KPI, Service Model, Business Pillar, Modernization Signals et posture du plan Defender for Cloud :

![Excel — Overview](docs/images/excel-overview.png)

Taxonomie de classification des ressources (Technical Category / Business Pillar / Service Model / Publisher) :

![Excel — Classification](docs/images/excel-classification.png)

Table plate `AllResources` :

![Excel — All Resources](docs/images/excel-allresources.png)

### Diagramme d’architecture draw.io

Organization — Tenant → Management Groups → Subscriptions :

![draw.io — Organization](docs/images/drawio-organization.png)

Network Topology — VNets / subnets / peerings, avec détection des ressources orphelines :

![draw.io — Network Topology](docs/images/drawio-network-topology.png)

Network Detail — ressources placées dans leurs subnets :

![draw.io — Network Detail](docs/images/drawio-network-detail.png)

Service Model — ressources regroupées par IaaS / PaaS / Hybrid / Supporting / Other :

![draw.io — Service Model](docs/images/drawio-service-model.png)

---

## Fonctionnalités principales

- **Couverture dynamique des types de ressources** — chaque type de ressource du tenant est découvert et capturé automatiquement. Les nouveaux types Azure sont traités de manière générique (sans modification du code) ; l’enrichissement par type est facultatif et cumulatif via `config/resource_enrichment.yaml`.
- **Classification granulaire des ressources** — *(Phase 3A)* Les ressources sont désormais classées avec un affinement du sous-espace de noms (par exemple, Azure Container Registry est distingué comme « Registry » et non « Registry Replication »). Les catégories techniques apparaissent dans Excel (`AllResources`, `Classification`, `ModernizationSignals` et `ResiliencyEvidence`) et dans la section « 📊 Technical Category Distribution » du rapport HTML technique.
- **Excel multifeuille structuré** — une feuille par type de ressource avec enrichissement déclaratif des propriétés, une table plate `AllResources` (désormais avec `Detailed Technical Category`), des tableaux croisés de classification par Service Model / Business Pillar / Technical Category, des matrices de résilience régionale, une feuille de navigation **Index** et une section **Data Collection Notes**.
- **Deux rapports HTML** — un rapport exécutif avec un **Executive Evidence Summary** factuel, un profil des piliers WAF, des KPI de posture des plans Defender, une vue de résilience et des signaux de modernisation clairement identifiés ; ainsi qu’un rapport technique comprenant les constatations par pilier WAF, Zero Trust, la posture Defender, les enregistrements de stratégies, les erreurs de configuration, l’intégrité, les ressources dépréciées et Technical Category Distribution. Les grandes tables/cartes prennent en charge `Load More` et `Show less`.
- **Diagramme d’architecture draw.io** — un fichier `.drawio` multipages avec de véritables icônes Azure : Overview (KPI + liens entre les pages), **Organization** (arborescence Tenant → Management Groups → Subscriptions avec le nombre de ressources), Service Model, Business Pillar, **Network Topology** (VNets/subnets/peering avec détection des peerings rompus), une page **Network Detail** (ressources placées dans leurs subnets : VMs, private endpoints, firewall, gateways, NSG shield, On-Premises node), une page **Security Posture** (cartes de risque par abonnement + badges de gravité sur les ressources) et une page Resources par abonnement. La carte des icônes est pilotée par la configuration avec une solution de secours générique, de sorte que les nouveaux types de ressources Azure sont automatiquement représentés. Ignorer avec `--no-diagram`.
- **Visibilité sur la sécurité, la gouvernance et les référentiels** — organise les constatations d’Azure Advisor, Policy, Defender for Cloud, Resource Health et des règles de configuration dans des vues alignées sur les piliers WAF, les principes de zone d’atterrissage CAF et les concepts Zero Trust.
- **Évaluation Cloud Modernization & Opportunity** — *(INFÉRÉE)* identifie les signaux observables d’adoption et de maturité dans les domaines Infrastructure, Application, Database, Data Platform, AI, Automation, Security, Governance/Landing Zone et Observability. Elle aide les équipes à déterminer où une découverte approfondie peut être utile, sans prescrire de parcours de migration ni de décision architecturale. Les signaux incluent le niveau de confiance, les éléments probants associés, les indicateurs d’opportunité et les références à WAF, CAF, ESLZ, AI-Ready et aux recommandations Defender.
- **Détection des erreurs de configuration fondée sur des règles** — règles issues de sources officielles et associées aux principes Zero Trust.
- **Détection de la conformité aux stratégies et des ressources dépréciées** — ressources non conformes et correspondances avec les annonces officielles de mise hors service Azure.
- **Posture Defender for Cloud** — activation des plans par abonnement, couverture des serveurs par ressource et coût de protection des écarts de couverture.
- **100 % en lecture seule** — données provenant exclusivement des API Azure officielles (Resource Graph, Advisor, Policy Insights, Resource Health et, facultativement, Defender et Cost Management).

---

## Prérequis

- **Python 3.9 ou version ultérieure**
- **Compte Azure** disposant au minimum d’un accès `Reader` sur les abonnements à analyser
- L’une des méthodes d’authentification suivantes :
  - `az login` (Azure CLI — recommandé pour une utilisation interactive locale ; aucun secret requis)
  - Managed Identity (en cas d’exécution sur une ressource de calcul Azure)
  - Service Principal au moyen de variables d’environnement (scénario d’automatisation avancé ; voir `.env.example`)

### Installer Azure CLI (facultatif mais recommandé)

```bash
# Windows (winget)
winget install -e --id Microsoft.AzureCLI

# macOS
brew install azure-cli

# Azure Cloud Shell — az CLI already installed and signed in
```

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/suellenferreira/azure-tenant-insights.git
cd azure-tenant-insights

# 2. (Recommended) Create a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Dépendances

```
azure-identity>=1.15.0
azure-mgmt-resourcegraph>=8.0.0
azure-mgmt-subscription>=3.1.1
requests>=2.31.0
openpyxl>=3.1.2
pyyaml>=6.0.1
```

---

## Démarrage rapide

```bash
# Authenticate via Azure CLI
az login

# Recommended first scan: scope to one subscription
python invoke_ati.py --subscription-id <SUBSCRIPTION-ID>

# Optional: scan all accessible subscriptions (interactive confirmation required)
python invoke_ati.py --tenant-id <TENANT-ID>

# Run against a specific tenant and subscription
python invoke_ati.py --tenant-id <TENANT-ID> --subscription-id <SUBSCRIPTION-ID>
```

Les fichiers de sortie sont enregistrés par défaut dans `./AzureTenantInsights/`.

> **Traitement des données :** les rapports générés contiennent des données relatives au tenant, aux abonnements, à l’inventaire des ressources, à la posture et éventuellement aux coûts. Traitez-les comme des artefacts opérationnels sensibles ; ne les ajoutez pas à un dépôt Git, ne les publiez pas et ne les partagez pas en dehors d’un stockage approuvé.

---

## Traitement des données client et clause de non-responsabilité relative à l’utilisation

ATI est un accélérateur d’évaluation open source en lecture seule. Il ne s’agit ni d’un produit Microsoft officiel, ni d’une certification de conformité, ni d’un substitut à une revue formelle d’architecture, de sécurité, financière, réglementaire ou juridique. ATI ne modifie pas les ressources Azure et n’effectue aucune remédiation automatique.

ATI s’exécute avec une identité, des autorisations Azure et une étendue d’évaluation sélectionnées et contrôlées par le client. Les rapports Excel, HTML et draw.io générés sont écrits uniquement dans le répertoire de sortie local ou la destination de stockage sélectionnée pour l’exécution. ATI ne charge ni ne transfère ailleurs le contenu des rapports générés. Comme les sorties peuvent contenir des métadonnées sensibles relatives à l’environnement Azure, le client doit approuver leur emplacement de stockage, leur accès, leur conservation et leur distribution conformément aux stratégies applicables.

Les résultats constituent un instantané et peuvent être incomplets en raison des autorisations, de la disponibilité des API, de la limitation de débit ou de collecteurs exclus. Certaines observations sont heuristiques ou reposent sur des catalogues locaux versionnés et nécessitent une validation avant toute décision de remédiation, d’investissement, de conformité ou d’architecture.

Vous pouvez exécuter ATI de manière autonome : vous définissez le périmètre de l’évaluation, fournissez et contrôlez l’identité en lecture seule utilisée pour l’exécution, choisissez l’emplacement de stockage des sorties et décidez comment les artefacts générés sont consultés, conservés et partagés. Suivez les processus juridiques, de confidentialité, de sécurité et de conformité de votre organisation lorsqu’une approbation formelle est requise.

---

## Utilisation

### Exemples de base

```bash
# Full tenant scan (all accessible subscriptions; interactive confirmation required)
python invoke_ati.py --tenant-id <TENANT-ID>

# Scope to specific subscription(s)
python invoke_ati.py --tenant-id <TENANT-ID> --subscription-id <SUB-ID-1> <SUB-ID-2>

# Scope to a Management Group (scans all subscriptions under it)
python invoke_ati.py --tenant-id <TENANT-ID> --management-group <MG-ID>

# All data sources are ON by default. Skip specific ones if needed:
python invoke_ati.py --tenant-id <TENANT-ID> --skip-costs        # exclude Cost Management
python invoke_ati.py --tenant-id <TENANT-ID> --skip-defender     # exclude Defender for Cloud
python invoke_ati.py --tenant-id <TENANT-ID> --skip-tags         # exclude tag columns from Excel

# Filter to specific resource group(s)
python invoke_ati.py --tenant-id <TENANT-ID> --resource-group rg-production rg-staging

# Filter by tag
python invoke_ati.py --tenant-id <TENANT-ID> --tag-key environment --tag-value production

# Optional: Service Principal authentication for automation
# Prefer environment variables so secrets are not stored in shell history.
export AZURE_TENANT_ID=<TENANT-ID>
export AZURE_CLIENT_ID=<APP-ID>
export AZURE_CLIENT_SECRET=<SECRET>
python invoke_ati.py

# Custom output directory and report name
python invoke_ati.py --tenant-id <TENANT-ID> \
  --output-dir ./reports \
  --report-name MyCompany_Quarterly

# Skip specific data sources for faster runs
python invoke_ati.py --tenant-id <TENANT-ID> \
  --skip-advisor \
  --skip-policy \
  --no-html

# Debug mode (verbose logging)
python invoke_ati.py --tenant-id <TENANT-ID> --debug
```

### Azure Cloud Shell

```bash
# Python & az are pre-installed and az is already signed in — just install the Python deps:
git clone https://github.com/suellenferreira/azure-tenant-insights.git
cd azure-tenant-insights
pip install -r requirements.txt --quiet
python invoke_ati.py
```

---

## Référence des paramètres

### Authentification

| Paramètre | Description |
|---|---|
| `--tenant-id <GUID>` | ID du tenant Azure. Facultatif — détecté automatiquement à partir du contexte `az login` |
| `--client-id <ID>` | ID d’application du Service Principal |
| `--client-secret <SECRET>` | Secret client du Service Principal. Pour l’automatisation, privilégiez `AZURE_CLIENT_SECRET` afin d’éviter son exposition dans l’historique du shell |

### Étendue

| Paramètre | Description |
|---|---|
| `--subscription-id <ID> [<ID> ...]` | Limiter l’analyse à un ou plusieurs abonnements spécifiques |
| `--management-group <ID>` | Analyser tous les abonnements sous un groupe d’administration |
| `--resource-group <NAME> [...]` | Limiter l’analyse à un ou plusieurs groupes de ressources spécifiques |
| `--tag-key <KEY>` | Filtrer les ressources par clé d’étiquette |
| `--tag-value <VALUE>` | Filtrer les ressources par valeur d’étiquette (requiert `--tag-key`) |

### Sources de données facultatives

Toutes les sources de données sont **activées par défaut**. Utilisez les indicateurs `--skip-*` pour les exclure :

| Paramètre | Description | RBAC supplémentaire requis |
|---|---|---|
| `--skip-defender` | Exclure les évaluations Defender for Cloud | — |
| `--skip-costs` | Exclure les données Cost Management | — |
| `--skip-tags` | Exclure les colonnes d’étiquettes de ressources d’Excel | — |
| `--skip-policy` | Exclure la collecte de conformité Azure Policy | — |
| `--skip-advisor` | Exclure les recommandations Azure Advisor | — |

### Sortie

| Paramètre | Description |
|---|---|
| `--output-dir <PATH>` | Répertoire de sortie (par défaut : `./AzureTenantInsights`) |
| `--report-name <NAME>` | Préfixe personnalisé des fichiers de rapport |
| `--no-excel` | Ignorer la génération de l’inventaire Excel |
| `--no-html` | Ignorer la génération des rapports HTML |
| `--no-diagram` | Ignorer la génération du diagramme d’architecture draw.io |
| `--network-detail-per-subscription` | Network Detail : une page par abonnement (pour les tenants très volumineux) |
| `--skip-org` | Ignorer la collecte de la hiérarchie des groupes d’administration (diagramme Organization) |
| `--no-security-overlay` | Désactiver la superposition Security Posture du diagramme (badges + page) |

### Performances

| Paramètre | Valeur par défaut | Description |
|---|---|---|
| `--throttle-delay <SECONDS>` | `1.0` | Délai entre les requêtes Resource Graph |
| `--cloud <NAME>` | `AzurePublicCloud` | Environnement cloud cible |

---

## Exigences RBAC

| Fonctionnalité | Rôle minimal | Étendue |
|---|---|---|
| Inventaire principal | `Reader` | Abonnement(s) |
| Conformité aux stratégies | `Reader` | Abonnement(s) |
| Azure Advisor | `Reader` | Abonnement(s) |
| Resource Health | `Reader` | Abonnement(s) |
| Étendue du groupe d’administration | `Reader` | Groupe d’administration |
| Posture des plans Defender | `Reader` | Abonnement(s) |
| Évaluations Defender for Cloud | `Security Reader` | Abonnement(s) |
| Données de coût | `Cost Management Reader` | Abonnement(s) ou compte de facturation |

> **Principe du moindre privilège :** ATI fonctionne à 100 % en lecture seule. Il n’apporte aucune modification aux ressources Azure.

---

## Fichiers de sortie

Les rapports générés peuvent inclure des métadonnées de tenant, des ID d’abonnement, des noms de ressources, des coûts, des constatations de sécurité et des détails de configuration. Conservez les fichiers générés localement par défaut et ne publiez pas les sorties `AzureTenantInsights/`, `*.xlsx`, `*.html` ou `*.log`.

Trois fichiers sont générés par exécution :

### `*_Inventory.xlsx` — Inventaire Excel

| Feuille | Contenu |
|---|---|
| `Overview` | Synthèse des KPI, principaux types de ressources, recommandations Advisor par pilier WAF, **Resource Origin** (Azure-native / Hybrid-Arc / Migrate), synthèse **Service Model** (IaaS/PaaS/SaaS/Hybrid/Supporting) et **Data Collection Notes** |
| `Index` | Feuille de navigation (placée après `Overview`) avec un lien hypertexte vers chaque onglet ; chaque feuille comporte un lien de retour **↩ Index** |
| `Classification` | **Taxonomie** des ressources par type — Technical Category, Business Pillar, Service Model, Publisher (Microsoft/Third-party) — avec tableaux croisés de synthèse (pilotés par la configuration) |
| `ModernizationSignals` | *(INFÉRÉ)* Cloud Modernization & Opportunity — score par dimension (0–100), niveau, confiance, signal inféré, éléments probants associés, indicateur d’opportunité et références aux référentiels |
| `Subscriptions` | Agrégation des ressources par abonnement, groupe de ressources, emplacement et type de ressource |
| `AllResources` | Table plate couvrant tous les types avec les colonnes communes Azure Resource Graph / ARM, une colonne **Category** (Azure-native / Hybrid-Arc / Migrate), les colonnes **Business Pillar** et **Service Model**, et les propriétés brutes |
| `[ResourceType]` | Une feuille par type de ressource utilisant les noms d’affichage configurés et l’enrichissement déclaratif des propriétés |
| `AdvisorFindings` | Toutes les recommandations Advisor avec le pilier WAF |
| `PolicyCompliance` | Ressources non conformes |
| `ResourceHealth` | Ressources dégradées/indisponibles |
| `DeprecatedResources` | Ressources correspondant aux annonces de mise hors service |
| `MisconfigFindings` | Erreurs de configuration connues |
| `SecurityAssessments` | Évaluations Defender for Cloud (omises avec `--skip-defender`) |
| `DefenderCostEstimate` | Coût estimé du plan Defender à partir de l’inventaire (omis avec `--skip-defender`) |
| `DefenderPosture` | Activation du plan Defender par abonnement via `Microsoft.Security/pricings` (omise avec `--skip-defender`) |
| `DefenderServersCoverage` | Couverture Defender for Servers par ressource pour VMs / VMSS / Arc Machines (omise avec `--skip-defender`) |
| `DefenderCoverageGap` | Unités facturables non protégées et **coût mensuel de protection** par plan (omis avec `--skip-defender`) |
| `Costs` | Coût par groupe de ressources/service (omis avec `--skip-costs`) |

> **Nommage des feuilles :** les noms des feuilles par type proviennent des noms d’affichage configurés ; un préfixe d’espace de noms court est ajouté **uniquement** lorsque deux fournisseurs seraient autrement en conflit (par exemple, `Cmp-Virtualmachinetemplates` et `VMw-Virtualmachinetemplates`). Chaque type de ressource obtient sa propre feuille jusqu’à la limite stricte de 255 d’Excel ; les autres restent dans `AllResources`. Un avertissement tenant compte de l’étendue est journalisé lorsque le nombre de feuilles de type est élevé (abonnement ≥ 40, groupe d’administration ≥ 60, tenant ≥ 75 ; valeurs modifiables par variable d’environnement).

### `*_Executive.html` — Rapport exécutif

Fichier HTML autonome. À ouvrir dans n’importe quel navigateur moderne — **aucune connexion Internet requise**.

- Bannière du niveau de risque global
- Vignettes de KPI (ressources, abonnements, constatations critiques, ressources dépréciées, couverture des étiquettes)
- Recommandations Advisor par pilier WAF (graphique en anneau)
- Principaux types de ressources (graphique à barres)
- Constatations les plus prioritaires (5, ou jusqu’à 10 pour les grands environnements)
- Synthèse de la posture des plans Defender et **écart de couverture** (unités facturables non protégées + coût mensuel estimé de protection) *(si les données Defender sont disponibles)*
- Recommandations stratégiques sous forme de **cartes colorées par priorité**
- Synthèse de la posture **Zero Trust** (avec code couleur par principe et descriptions)
- Signaux de modernisation *(étiquetés comme INFÉRÉS)*
- Sections réductibles avec les contrôles **Expand All / Collapse All** ; lien discret vers **Data Collection Notes**

### `*_Technical.html` — Rapport technique

Fichier HTML autonome avec navigation dans la barre latérale.

- Synthèse de l’inventaire des ressources ; graphique **Resources by Subscription** libellé par nom d’abonnement
- Constatations par pilier WAF (onglets par pilier) avec **chargement progressif** (30 lignes à la fois ; les longues listes renvoient vers l’exportation Excel) et **recherche par colonne**
- Violations de conformité aux stratégies
- Erreurs de configuration connues (liées à la documentation officielle)
- Évaluations Defender for Cloud *(omises avec `--skip-defender`)*
- **Posture des plans** Defender (plans activés/désactivés par abonnement, avec **recherche par colonne**) et couverture des serveurs par ressource *(si les données Defender sont disponibles)*
- Table des **écarts de couverture et coûts de protection** Defender (unités facturables non protégées × prix unitaire par plan) *(si les données Defender sont disponibles)*
- Événements d’intégrité des ressources
- Ressources dépréciées/en cours de retrait avec liens de migration
- Observations relatives à la zone d’atterrissage *(étiquetées comme INFÉRÉES)*
- Ressources Azure Arc *(si présentes)*
- Sections réductibles avec **Expand All / Collapse All** ; lien discret vers **Data Collection Notes**

> **Remarque sur les graphiques :** les rapports utilisent [Chart.js](https://www.chartjs.org/) chargé depuis le CDN (`cdn.jsdelivr.net`). Une connexion Internet est nécessaire pour afficher les graphiques. Toutes les tables de données restent visibles sans connexion Internet.

### `*_Diagram.drawio` — Diagramme d’architecture

Fichier [draw.io](https://app.diagrams.net) multipages (XML non compressé) avec de véritables icônes Azure. Le fichier `.drawio` contient un diagramme modifiable, et non une image ; GitHub ne l’affiche pas directement.

**Comment ouvrir le diagramme généré :**

1. **diagrams.net Web :** accédez à [app.diagrams.net](https://app.diagrams.net), sélectionnez **Device**, puis **File > Open From > Device** et sélectionnez le fichier `.drawio` généré.
2. **diagrams.net Desktop :** installez l’[application de bureau](https://github.com/jgraph/drawio-desktop/releases) et ouvrez le fichier localement.
3. **VS Code :** installez une extension d’intégration Draw.io approuvée par le client et ouvrez le fichier `.drawio` dans l’éditeur.

Le diagramme peut contenir des métadonnées sensibles relatives à l’environnement Azure. Utilisez des outils approuvés par le client et respectez la stratégie applicable de traitement des données, en particulier avant d’utiliser l’option Web.

Pages :

- **Overview** — KPI par Service Model et Business Pillar, avec liens cliquables vers chaque page
- **Organization** — arborescence Tenant → Management Groups → Subscriptions avec le nombre de ressources par abonnement
- **Service Model** / **Business Pillar** — types de ressources regroupés par IaaS/PaaS/SaaS/… et par pilier métier
- **Network Topology** — VNets, subnets et peering (vert = Connected, tirets rouges = Disconnected/orphan), regroupés par abonnement
- **Network Detail** — ressources placées dans leurs subnets (VMs, private endpoints, firewall, gateways, NSG shield, On-Premises node)
- **Security Posture** — cartes de risque par abonnement (couverture Defender, Zero Trust) et badges de gravité sur les ressources Network Detail *(lorsque les données de sécurité sont disponibles)*
- **Resources** — une page par abonnement avec des conteneurs de groupes de ressources

Les icônes proviennent des gabarits Azure 2019 intégrés à draw.io, avec une solution de secours générique afin que les tout nouveaux types de ressources soient eux aussi représentés par une icône. Ignorez la génération avec `--no-diagram` ; utilisez `--network-detail-per-subscription` pour obtenir une page Network Detail par abonnement et `--no-security-overlay` pour désactiver les badges/la page de sécurité.

---

## Structure du projet

```
azure-tenant-insights/
│
├── invoke_ati.py                   ← Point d’entrée principal
├── requirements.txt
├── pyproject.toml
├── README.md                       ← Anglais
├── README.fr.md                    ← Ce fichier (Français)
├── README.pt-BR.md                 ← Portugais (Brésil)
├── README.es.md                    ← Espagnol
├── CHANGELOG.md
│
├── config/
│   ├── resource_enrichment.yaml    ← Règles de promotion des propriétés par type
│   ├── resource_classification.yaml ← Taxonomie à 3 niveaux (Service Model / Business Pillar)
│   ├── deprecated_types.json       ← Annonces connues de mise hors service Azure
│   ├── misconfiguration_rules.yaml ← Définitions des règles de sécurité/configuration
│   ├── drawio_stencils.yaml        ← Mappage type de ressource → icône Azure (diagramme)
│   ├── network_placement.yaml      ← Résolution ressource → subnet (Network Detail)
│   └── security_overlay.yaml       ← Couleurs de gravité + mappage Zero Trust (diagramme)
│
├── collectors/                     ← Collecte de données des API Azure
│   ├── auth.py                     ← Authentification (DefaultAzureCredential / SP)
│   ├── subscriptions.py            ← Énumération des abonnements
│   ├── resource_graph.py           ← Moteur Resource Graph paginé principal (nouvelle tentative/backoff CLI)
│   ├── resources.py                ← Collecte dynamique des ressources
│   ├── advisor.py                  ← Recommandations Azure Advisor
│   ├── policy.py                   ← États de conformité Azure Policy
│   ├── health.py                   ← Événements Resource Health
│   ├── defender.py                 ← Évaluations Defender for Cloud
│   ├── defender_posture.py         ← Posture des plans Defender (Microsoft.Security/pricings)
│   ├── defender_pricing.py         ← Écart de couverture + tarification en direct (Azure Retail Prices API)
│   ├── costs.py                    ← Données Cost Management
│   └── mgmt_groups.py              ← Hiérarchie des groupes d’administration (diagramme Organization)
│
├── processors/                     ← Enrichissement et analyse des données
│   ├── normalizer.py               ← Utilitaires de normalisation des chaînes/types
│   ├── deprecation.py              ← Détection des ressources dépréciées
│   ├── waf_mapper.py               ← Regroupement par pilier WAF
│   ├── misconfig_detector.py       ← Évaluation des règles de mauvaise configuration
│   ├── classifier.py               ← Taxonomie de classification des ressources
│   ├── org_tree.py                 ← Arborescence Tenant → MG → Subscription (diagramme)
│   ├── network_topology.py         ← Graphe VNet/subnet/peering (diagramme)
│   ├── network_detail.py           ← Placement des ressources dans les subnets (diagramme)
│   ├── security_overlay.py         ← Risque par ressource/abonnement (diagramme)
│   └── summary.py                  ← Calcul des métriques KPI
│
└── writers/                        ← Génération des sorties
    ├── excel_writer.py             ← Générateur de classeur Excel (openpyxl)
    ├── html_executive.py           ← Rapport HTML exécutif
    ├── html_technical.py           ← Rapport HTML technique
    └── drawio_writer.py            ← Diagramme d’architecture draw.io multipages
```

---

## Fichiers de configuration

Les fichiers sous `config/` sont des catalogues locaux gérés par le contrôle de version. ATI les évalue pendant l’analyse, mais ne récupère, ne valide ni ne met à jour leurs règles à partir de Microsoft Learn ou de GitHub lors de l’exécution. `config/catalog_metadata.json` enregistre la version du catalogue, la date de vérification, la provenance et les sections de rapport concernées.

La fraîcheur du catalogue est calculée localement à chaque analyse : `current` jusqu’à 90 jours, `review_due` de 91 à 180 jours et `stale` au-delà de 180 jours. Lorsque l’état est `review_due` ou `stale`, l’administrateur est averti qu’il doit valider la version du catalogue installée. Le rapport HTML technique affiche des indicateurs contextuels et une table centrale **Catalog Status** ; Excel comprend une feuille `CatalogStatus` ; draw.io consigne la version du catalogue sur sa page Overview. Seuls les catalogues `stale` produisent une clause de non-responsabilité dans le rapport HTML exécutif. Les avertissements ne bloquent pas les analyses et ne modifient pas automatiquement les catalogues locaux.

### `config/resource_enrichment.yaml`

Définit les champs `properties.*` imbriqués à promouvoir en colonnes nommées pour chaque type de ressource. Les ressources sans entrée de règle sont tout de même collectées — leur JSON `properties` brut est stocké dans la feuille `AllResources`.

Les champs promus doivent reposer sur des références Microsoft officielles, principalement la [référence des tables et types de ressources Azure Resource Graph](https://learn.microsoft.com/en-us/azure/governance/resource-graph/reference/supported-tables-resources) et les [définitions de ressources des modèles Azure Resource Manager](https://learn.microsoft.com/en-us/azure/templates/). Considérez les colonnes suggérées comme un point de départ ; vérifiez les propriétés du fournisseur dans Microsoft Learn avant de les ajouter.

Pour ajouter un enrichissement pour un nouveau type de ressource :

```yaml
resource_types:
  "microsoft.newservice/resourcetype":
    display_name: "My New Resource"
    promoted_fields:
      - path: "properties.someProperty"
        column: "some_property"
```

### `config/deprecated_types.json`

Contient les annonces connues de mise hors service Azure. Chaque entrée précise le type de ressource, la date de retrait, la gravité ainsi que les liens vers l’annonce officielle et le parcours de migration.

Mettez à jour ce fichier lorsque de nouvelles annonces de mise hors service sont publiées dans [Azure Updates](https://azure.microsoft.com/en-us/updates/).

### `config/misconfiguration_rules.yaml`

Définit les contrôles heuristiques locaux de configuration pour des types de ressources spécifiques. Les règles reposent sur la documentation Microsoft associée, mais ne sont pas revalidées en ligne pendant une analyse. Les constatations d’Azure Policy et Defender restent les résultats d’API faisant autorité. Opérateurs pris en charge : `equals`, `not_equals`, `equals_true`, `equals_false`, `is_null`, `is_not_null`, `contains`, `not_contains`.

### Mises à jour des catalogues

Adoptez les catalogues mis à jour par le biais d’une version ATI révisée, d’un `git pull` contrôlé ou d’un nouveau clone. Validez la modification avant toute utilisation chez un client. Le dépôt officiel exécute `.github/workflows/catalog-maintenance.yml` chaque mois afin de générer une PR destinée uniquement à la révision. Sa tâche est limitée à `suellenferreira/azure-tenant-insights` ; les clones et analyses des clients restent hors ligne et épinglés à la version locale de leur catalogue.

---

## Environnements cloud pris en charge

| Indicateur | Environnement |
|---|---|
| `AzurePublicCloud` | Azure Global (par défaut) |
| `AzureUSGovernment` | Azure US Government |
| `AzureChinaCloud` | Azure China (21Vianet) |
| `AzureGermanCloud` | Azure Germany |

---

## Durée d’exécution estimée

| Taille du tenant | Durée d’exécution estimée |
|---|---|
| < 500 ressources | ~2 minutes |
| 500–5 000 ressources | ~5–15 minutes |
| 5 000–50 000 ressources | ~15–60 minutes |
| > 50 000 ressources | > 60 minutes (planification pendant la nuit recommandée) |

Pour les tenants volumineux, envisagez d’utiliser `--skip-advisor`, `--skip-policy` ou `--no-html` afin de réduire la durée d’exécution.

---

## Limitations

- **Limite de page Resource Graph :** 1 000 enregistrements/page. La pagination est gérée automatiquement.
- **Limitation de débit :** Resource Graph limite le débit des requêtes par utilisateur. ATI respecte `Retry-After` sur les réponses `429`, utilise par défaut 30 secondes lorsque la valeur n’est pas disponible, plafonne chaque attente à 120 secondes et réessaie chaque page jusqu’à cinq fois. Les pages terminées sont conservées si les nouvelles tentatives sont épuisées. Utilisez `--throttle-delay` pour réduire de manière proactive la fréquence des requêtes.
- **Toutes les propriétés ne sont pas exposées :** Resource Graph utilise la dernière API non-preview pour chaque type. Certaines propriétés disponibles uniquement en préversion peuvent ne pas apparaître.
- **Les données de coût nécessitent un RBAC élevé :** le rôle `Cost Management Reader` est requis, ce qui est supérieur au rôle `Reader`.
- **Les estimations de coût Defender sont approximatives :** les prix unitaires sont récupérés en direct depuis l’API publique Azure Retail Prices (tarification publique **catalogue**). Lorsque l’API est inaccessible, des prix de secours intégrés sont utilisés et les rapports les signalent comme une solution de secours hors ligne potentiellement obsolète. Les remises EA/MCA/CSP, les niveaux gratuits et les plans basés sur l’utilisation (par exemple Cosmos DB) ne sont pas pris en compte.
- **Les graphiques nécessitent Internet :** Chart.js est chargé depuis un CDN. Toutes les tables de données s’affichent sans connexion Internet.
- **Instantané uniquement :** ATI produit des instantanés. L’analyse des tendances nécessite la planification d’exécutions régulières.
- **Les signaux de modernisation sont INFÉRÉS :** aucune API Azure officielle ne renvoie de score de préparation à l’IA ou de modernisation. ATI les infère uniquement à partir des types de ressources détectés.

---

## Résolution des problèmes

| Symptôme | Cause probable | Correction |
|---|---|---|
| `Authentication failed` / aucun abonnement trouvé | Session non ouverte ou tenant incorrect | Exécutez `az login` (ou `az login --tenant <ID>`) ; confirmez avec `az account show` |
| `AuthorizationFailed` / `403` dans le journal pour certaines données | RBAC manquant sur un abonnement | Assurez-vous de disposer au minimum du rôle `Reader` ; ajoutez `Security Reader` (Defender) / `Cost Management Reader` (coûts), ou utilisez `--skip-defender` / `--skip-costs` |
| L’analyse est lente ou journalise `429 TooManyRequests` | Limitation de débit Resource Graph | ATI réessaie chaque page jusqu’à cinq fois à l’aide de `Retry-After` (valeur de secours de 30 secondes, plafond de 120 secondes). Augmentez `--throttle-delay` (par exemple `2.0`) ou réduisez l’étendue si la limitation persiste. |
| L’exécution dure longtemps | L’étendue par défaut comprend **tous** les abonnements du tenant | Limitez l’étendue de l’analyse ou passez `-y` pour ignorer la confirmation |
| Blocage à l’invite « Custom Report Name » dans CI | Aucun terminal interactif (TTY) | Passez `--report-name <NAME>` ou `-y` (les deux ignorent l’invite) |
| Les graphiques ne s’affichent pas | Hors ligne / CDN bloqué | Les tables de données fonctionnent toujours hors ligne ; les graphiques nécessitent `cdn.jsdelivr.net` |
| Le fichier `.drawio` ne s’ouvre pas ou s’affiche comme du XML/texte | Aucun visualiseur compatible diagrams.net n’est sélectionné | Ouvrez [app.diagrams.net](https://app.diagrams.net), sélectionnez **Device**, puis **File > Open From > Device** ; vous pouvez également utiliser diagrams.net Desktop ou une extension VS Code approuvée. |
| Journaux HTTP très détaillés | `--debug` activé | Omettez `--debug` ; le SDK Azure masque les jetons sous la forme `REDACTED` |

> **L’authentification Service Principal** lit `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` depuis **l’environnement**. Exportez-les (ou utilisez simplement `az login`) — un fichier `.env` n’est pas chargé automatiquement.

---

## Contribution

1. Dupliquez le dépôt
2. Créez une branche de fonctionnalité : `git checkout -b feature/my-improvement`
3. Apportez les modifications et testez-les sur un abonnement Azure réel
4. Soumettez une Pull Request avec une description claire

Pour ajouter une nouvelle règle de mauvaise configuration, modifiez `config/misconfiguration_rules.yaml` et fournissez :
- Un `id` unique
- Une référence à la documentation Microsoft officielle dans `documentation_url`
- Les valeurs exactes de `condition_path` et `expected_value` provenant de la documentation officielle de l’API

---

## Licence

Licence MIT — consultez [LICENSE](./LICENSE) pour plus de détails.

> Ce projet n’est pas un produit Microsoft officiel. Il utilise uniquement des API Azure officielles et publiquement documentées.
