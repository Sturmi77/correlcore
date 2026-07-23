# [FEATURE] Group heatmaps by Tag Groups (co-occurrence clusters)

> Ready-to-paste GitHub issue body (feature_request template).
> Labels: `enhancement`
> Milestone: Backlog / Insights

---

## Feature-Beschreibung

Heatmap-Achsen nach berechneten **Tag Groups** (Co-Occurrence-Cluster) gruppieren und optional filtern — Tags, die gemeinsam vorkommen, räumlich zusammen und per Gruppe fokussierbar.

## Problem / Motivation

Tag Groups ([`tag_cluster_service.py`](../../backend/app/services/tag_cluster_service.py), `GET /insights/tag-clusters`, [`TagGroupsSection`](../../apps/web/src/lib/components/insights/TagGroupsSection.svelte)) und Co-Occurrence-Heatmaps existieren parallel **ohne gemeinsame UI**. Der Sort-Modus `clustered` ist nur clientseitige Hierarchical-Order, nicht Server-`cluster_id`. Nutzer können Heatmaps nicht nach „Clustern gemeinsam vorkommender Tags“ lesen.

## Vorgeschlagene Lösung

1. **Primär (Insights Co-Occurrence):** Wenn `tag-clusters` Status `ok`, Mapping `tagId → cluster_id` bauen.
2. Neuer Sort/Filter-Modus an Tag- und Symptom-Co-Occurrence-Heatmaps: Achsen nach `cluster_id` dann Slug; visuelle Gruppenlücken; „Focus cluster“-Chips (Klick aus `TagGroupsSection`).
3. Fallback: bisheriges hierarchical `clustered`, wenn Clusters `insufficient_data`.
4. **Sekundär:** denselben Row-Order-Modus optional auf Trends `ComparisonHeatmap` / Tag-Kalender — clientseitig nach Fetch.
5. Kein neues Clustering; Fenster-Hinweis (Clusters ~90d vs. wählbare Heatmap-Range).

### Umsetzungsplan

Shared `tagId→cluster` Helper → Co-Occurrence Sort/Filter + UI-Chips → i18n → optional Trends → Tests.

## Alternativen

- User-editierbare Tag Groups — Scope-Explosion; Finding meint berechnete Cluster.
- Nur Kalender-Heatmaps clustern — schwächerer Signal-Fit als Co-Occurrence-Heatmaps.

## Milestone

Backlog / Insights

## Datenschutz-Impact

Nur Reorder/Filter bestehender Aggregate; keine neuen Tracking-Daten.
