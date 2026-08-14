# Research Log — DataSense Market Discovery

**Reference date:** 2026-08-14

## Source 1 — Gartner C-level Communities / Evanta

- URL: https://www.evanta.com/resources/cdao/survey-report/top-3-priorities-for-cdaos-in-2025
- Accessed: 2026-08-14
- Evidence: the page describes an early-2025 Leadership Perspective Survey of 850 CDAOs. It identifies Generative/Traditional AI, Data & Analytics Strategy, and Data Governance as the three leading functional priorities. It also states that governance has been a top focus for five consecutive years, while increased AI activity renewed attention on data quality, observability and stewardship.
- Relevance to DataSense: supports the problem urgency, but does not validate DataSense-specific willingness-to-pay or market size.

## Source 2 — Microsoft Purview documentation

- URL: https://learn.microsoft.com/en-us/purview/data-governance-overview
- Accessed: 2026-08-14
- Evidence: Microsoft frames governance around data being discoverable, accurate, trusted and protected. Its documented capabilities include catalog/data map, built-in data quality and lineage, governance domains, and reader/owner role-based access.
- Relevance to DataSense: confirms that catalog/lineage/RBAC/data-quality are incumbent enterprise expectations. It also clarifies DataSense should not compete head-on as a global catalog at the current stage; the more differentiated near-term wedge is local-first, analyst-side trust evidence before report/export.

## Working implication

The current evidence supports a focused beachhead: teams with Windows-based analyst workflows and sensitive tabular data where evidence must exist before an analytical deliverable leaves the team. It does **not** yet support a claim about global market size, a precise pricing level, or a winning geography. Those require further sourcing and customer discovery.

## Source 3 — Soda

- URL: https://www.soda.io/
- Accessed: 2026-08-14
- Evidence: Soda markets automated data quality, data observability, data contracts, smart thresholds, feedback-assisted anomaly handling, record-level diagnostics, lineage/impact and auditable permission-controlled collaborative workflows. Its position is production data systems and scalable monitoring, rather than a local analyst desktop.
- Competitive implication: DataSense should avoid framing against Soda on “automated observability at warehouse scale.” A credible differentiation is pre-publication trust evidence in the analyst’s local Windows workflow, with optional policy-compatible hand-off to enterprise operations.

## Source 4 — Great Expectations

- URL: https://greatexpectations.io/
- Accessed: 2026-08-14
- Evidence: GX Core is an Apache 2.0 open-source data-quality framework oriented around Python/Jupyter, Expectations, Data Docs and orchestrator integration. The vendor presents it as a shared tool for technical teams that can block bad data, prevent downstream movement and notify teams.
- Competitive implication: DataSense cannot claim exclusive ownership of contracts or data-quality checks. Its viable wedge is a no-code, Windows-native UX for analysts that exposes the same class of evidence before code/pipeline engineering is required; interoperability/export may lower buyer risk.

## Preliminary white-space hypothesis

A potential white space exists between code-first/open-source validation and warehouse-scale observability platforms: **local-first, evidence-first analytics governance for spreadsheet/CSV/SQL extract workflows**. Confidence is currently medium-low because it needs direct user interviews and a pricing comparison, not only competitor websites.

## Source 5 — Eurostat (discovery signal)

- URL: https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Digital_economy_and_society_statistics_-_enterprises
- Accessed: 2026-08-14
- Browser extraction was incomplete, so no unverified statistic from this URL is used as a hard model input. Search discovery indicated that Eurostat publishes enterprise digitalisation data by size class, including self-reported data-analytics usage. This source remains a candidate for later country-level sizing and must be re-extracted from the underlying table before use.

## Source 6 — U.S. Census Bureau

- URL: https://www.census.gov/library/stories/2026/05/small-business-week.html
- Accessed: 2026-08-14
- Evidence: the Census Bureau reports 5.58 million U.S. firms with at least one employee and fewer than 500 employees in 2023, compared with 5.53 million in 2022.
- Relevance: this is an upper-bound logo universe only. It must not be treated as DataSense TAM: vertical, size, analytics maturity, Windows workflow, regulatory need and channel-access filters are required before it enters a SAM/SOM build.

## Source 7 — Alteryx

- URL: https://www.alteryx.com/
- Accessed: 2026-08-14
- Evidence: Alteryx presents a unified platform across data ingestion/extraction/preparation/enrichment, AI analytics, workflow automation/orchestration, reporting, workspace collaboration and governance. It explicitly targets both SMB and enterprise verticals.
- Competitive implication: Alteryx is a direct alternative for self-service analytics workflow, but DataSense should not chase feature parity. The strategic response is a constrained wedge: a lighter Windows path from dataset to governed evidence, aimed at teams where report defensibility precedes platform-scale automation.

## Source 8 — KNIME

- URL: https://www.knime.com/knime-for-enterprise
- Accessed: 2026-08-14
- Evidence: KNIME Business Hub positions on secure governance/control, audit trails, trusted AI providers, PII guardrails, centralized administration and SaaS or self-hosted deployment options.
- Competitive implication: enterprise buyers will evaluate DataSense against platform-level control and deployment flexibility even if the first user is an analyst. DataSense should therefore publish an honest staged enterprise path (SSO, signed evidence, private deployment, audit/DR) rather than make unsupported feature-parity claims.

## Competitive conclusion so far

The market is crowded at both ends: code-first quality tooling and mature enterprise analytics platforms. A defensible entry point is not generic “governed analytics.” It is a concrete promise: **make a local analysis explainable and auditable before it becomes a report, export or decision input**. The next research step must test whether buyers recognize this as an independent budget line or only as a feature of an incumbent platform.

## Source 9 — Eurostat Structural Business Statistics

- URL: https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Structural_business_statistics_overview
- Accessed: 2026-08-14; data extracted September 2025, mostly for 2023.
- Evidence: Eurostat reports 33.1 million active EU enterprises in 2023, 99.8% of which were SMEs. Professional, scientific and technical activities represented 15.6% of EU business-economy enterprises; financial and insurance was material in value added but had a smaller workforce.
- Relevance: the EU is a large potential market, but the statistic is not an addressable-customer count. DataSense would still need country, language, procurement, regulatory and channel filters before converting it to any TAM/SAM model.

## Source 10 — UK Office for National Statistics

- URL: https://www.ons.gov.uk/businessindustryandtrade/business/activitysizeandlocation/bulletins/ukbusinessactivitysizeandlocation/2025
- Accessed: 2026-08-14; reference point March 2025.
- Evidence: the ONS counted 2,734,615 VAT and/or PAYE businesses. Professional, scientific and technical activities was the largest industry group at 15.3% of registered businesses. The data set is based on the UK Inter-Departmental Business Register and excludes parts of the unregistered business population.
- Relevance: the UK is a tractable English-language test market with a significant professional-services universe, but business count is an upper bound rather than demand evidence. A pilot should target a narrow workflow and named buyer persona rather than market broadly to all registered firms.

## Current beachhead recommendation — decision quality: medium

Start commercial discovery with **English-language professional-services, financial-operations and regulated-analytics teams with 50–5,000 employees**, initially using the UK and North American design-partner pipeline. The market choice is based on language, existing Windows analyst workflows, auditable reporting needs and accessible firm universe; it is not a claim that either geography is the largest or cheapest market. EU expansion should follow only after localization, residency and procurement requirements are explicitly covered.
