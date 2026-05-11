# ADR-0001: SvelteKit als Web-Framework (statt Next.js)

**Status:** Akzeptiert
**Datum:** 2026-04-20
**Kontext:** Auswahl des Web-Frontend-Frameworks für die PWA

---

## Kontext

Für die CorrelCore-PWA wird ein Framework benötigt, das:

- Kleine Bundle-Größen produziert (Performance-Budget: JS < 150 KB gz)
- Gute Offline-/PWA-Unterstützung bietet
- Von einem Solo-Dev effizient bedient werden kann
- Dark-Mode und i18n nativ unterstützt

## Entscheidung

**SvelteKit 2** mit **Skeleton UI** als Komponenten-Bibliothek.

## Begründung

| Kriterium         | SvelteKit                                       | Next.js                             |
| ----------------- | ----------------------------------------------- | ----------------------------------- |
| Bundle-Größe      | ~30–80 KB gz (kein Virtual DOM)                 | ~150–300 KB gz (React overhead)     |
| Performance       | Compile-time Optimierung, kein Runtime-Overhead | Hydration-Overhead                  |
| Lernkurve         | Niedriger für Solo-Dev                          | Höher (React-Ökosystem-Komplexität) |
| PWA-Support       | Gut (via `@vite-pwa/sveltekit`)                 | Gut (via `next-pwa`)                |
| Community         | Kleiner, aber wachsend                          | Sehr groß                           |
| Employer Branding | Gut für Portfolio-Differenzierung               | Standard                            |

Next.js wäre die sichere Wahl bei Team-Erweiterung (mehr React-Devs am Markt). Für ein Solo-Projekt, das Performance-sensitiv und Bundle-bewusst ist, überwiegen die SvelteKit-Vorteile.

## Konsequenzen

- **Positiv:** Kleinere Bundles, einfacheres Reaktivitätsmodell, schnellere Compile-Zeiten
- **Negativ:** Weniger Komponenten-Bibliotheken verfügbar als für React; bei Teamwachstum ggf. Migration nötig
- **Neutral:** TWA via Bubblewrap funktioniert unabhängig vom Frontend-Framework (basiert auf der PWA-URL)

## Revisionshinweis

Falls das Team auf > 3 Entwickler wächst oder eine React-native iOS-App benötigt wird, ADR-0001 revisiten.
