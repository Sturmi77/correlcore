# CorrelCore — Frontend-Prinzipien

Dieses Dokument leitet sich aus [`DESIGN_DOCUMENT.md`](DESIGN_DOCUMENT.md) ab.

---

## 1. Kerngrundsätze

### 60-Sekunden-Regel

Der Default-Eintrag muss in ≤ 60 Sekunden abgeschlossen sein:

- Mood-Slider (Pflicht)
- 3 Top-Tags (Optional, schnell auswählbar)
- Symptome (Optional)
- Notiz (Optional)

Jede Komponente, die diesen Flow verlangsamt, ist zu überdenken.

### Mobile First

- Breakpoints: 375px (Basis) → 768px → 1024px+
- Touch-Targets: ≥ 44×44 px (WCAG 2.5.5)
- Bottom-Sheet statt Full-Page-Form für Entry-Erstellung
- Swipe-Gesten für Navigation (Heute ↔ Gestern ↔ Insights)

### Home-Screen-Philosophie

```
┌─────────────────────┐
│  Heute, 20. April   │
│  [Streak: 🔥 7]     │
│                     │
│  [Insight-Karte]    │
│  "An Sport-Tagen..."│
│                     │
│  [Eintrag erstellen]│
└─────────────────────┘
```

Keine Dashboard-Überladung. Maximal 3 Informationsbereiche auf dem Home-Screen.

---

## 2. Tech-Stack

| Technologie              | Begründung                                                    |
| ------------------------ | ------------------------------------------------------------- |
| **SvelteKit 2**          | Kleinstes Bundle, SSR/CSR flexibel, native Transitions        |
| **Skeleton UI**          | SvelteKit-native, themeable, Dark-Mode-Support                |
| **Dexie.js**             | IndexedDB-Abstraktion für Offline-Sync                        |
| **ECharts / LayerChart** | Mobile-freundliche Charts (Entscheidung noch offen, ADR-0002) |
| **pnpm**                 | Schnelleres Package Management im Monorepo                    |
| **Vite**                 | Fast HMR, optimiertes Bundling                                |

---

## 3. Performance-Budget

| Metrik                         | Ziel     |
| ------------------------------ | -------- |
| JS Bundle (gz)                 | < 150 KB |
| LCP (Largest Contentful Paint) | < 2,0 s  |
| TTI (Time to Interactive)      | < 3,0 s  |
| CLS                            | < 0,1    |
| FID / INP                      | < 100 ms |

Tools: Lighthouse CI in CI/CD-Pipeline, Web Vitals Monitoring via GlitchTip.

---

## 4. Design-System

### Theming

```css
/* CSS Custom Properties */
:root[data-theme='dark'] {
  --color-bg: #0f1117;
  --color-surface: #1a1d27;
  --color-primary: #7c6af5;
  --color-text: #e8eaf0;
  --color-text-muted: #8b8fa8;
}

:root[data-theme='light'] {
  --color-bg: #f8f9fc;
  --color-surface: #ffffff;
  --color-primary: #6356d9;
  --color-text: #1a1d27;
  --color-text-muted: #6b7280;
}
```

- System-Preference via `prefers-color-scheme` als Default
- Manueller Override via `data-theme`-Attribut auf `<html>`
- Persistenz in LocalStorage

### Mood-Score-Farben

```
-2 (sehr schlecht) → #ef4444 (rot)
-1 (schlecht)      → #f97316 (orange)
 0 (neutral)       → #94a3b8 (grau)
+1 (gut)           → #84cc16 (hellgrün)
+2 (sehr gut)      → #22c55e (grün)
```

Farbe darf **nie** die einzige Information sein — immer Label oder Icon ergänzen (WCAG 1.4.1).

---

## 5. Accessibility (WCAG 2.2 AA)

- Alle interaktiven Elemente per Keyboard navigierbar
- Mood-Slider: zusätzlich mit +/- Buttons bedienbar (für Screenreader + Motor-Einschränkungen)
- Farbkontrast: ≥ 4,5:1 (Normal Text), ≥ 3:1 (Large Text)
- Focus-Outline sichtbar und nicht entfernt
- ARIA-Labels für alle Icon-only-Buttons
- `prefers-reduced-motion`: Animationen deaktiviert / minimiert

---

## 6. Internationalisierung (i18n)

- **Ab Tag 1:** DE und EN
- Keine Hardcoded Strings im Template-Code
- Bibliothek: `svelte-i18n` oder `paraglide-js`
- Locale-Dateien unter `apps/web/src/locales/de.json` und `en.json`
- Datumsformate: `Intl.DateTimeFormat` (locale-aware)
- RTL-Unterstützung: kein Ziel für v1, aber keine Breaking-Choices treffen

---

## 7. Komponenten-Struktur (Atomic Design)

```
apps/web/src/
├── lib/
│   ├── atoms/          # Button, Input, Badge, Icon, Slider
│   ├── molecules/      # MoodSlider, TagPicker, SymptomChecker
│   ├── organisms/      # EntryForm, InsightCard, StreakWidget
│   ├── templates/      # PageLayout, BottomSheetLayout
│   └── stores/         # Svelte Stores (entries, sync, insights)
├── routes/
│   ├── +page.svelte    # Home-Screen
│   ├── entry/          # Entry Create/Edit
│   ├── insights/       # Insights & Visualisierungen
│   └── settings/       # User-Einstellungen
└── locales/
    ├── de.json
    └── en.json
```

Storybook für alle Atoms und Molecules.

---

## 8. Motion & Animationen

- **Dauer:** 150–250 ms für Standard-Transitions
- **Easing:** `ease-out` für Einblendungen, `ease-in` für Ausblendungen
- **Reduced Motion:** `@media (prefers-reduced-motion: reduce)` → `transition: none`
- **Keine Layout-Shifts** durch Animationen (CLS-Budget)

```css
/* Standard Transition */
.fade-in {
  animation: fadeIn 200ms ease-out;
}

@media (prefers-reduced-motion: reduce) {
  .fade-in {
    animation: none;
  }
}
```

---

## 9. Authentifizierung (Issue #40)

### Strategie

- **Mechanismus:** HttpOnly-Cookies (`SameSite=Strict`, `Secure` in Prod), kein Token im JavaScript-Heap.
- **Begründung:** Maximale Resistenz gegen XSS auf DSGVO Art.-9-Daten — siehe ADR-0004.
- **Refresh:** `apiFetch` setzt auf 401 genau einen `/auth/refresh` ab und wiederholt den Original-Request. Single-Flight-Pattern: parallele 401s teilen sich die selbe Refresh-Promise; es wird nie mehr als eine `/auth/refresh`-Anfrage gleichzeitig gestellt.
- **Phase 2 (Capacitor, M11+):** `capacitor://`-Schema blockiert Third-Party-Cookies. Der Migrationspfad ist im selben `apiFetch`-Interface umgesetzt: das Backend liefert `access_token` bereits im Body (siehe `TokenResponse`), und `apiFetch` wird in der Capacitor-Build-Variante auf einen In-Memory-Bearer-Header umgestellt. Eigener ADR-Entry folgt bei M11-Start.

### Routen

| Route                       | Zweck                                                   | Public |
| --------------------------- | ------------------------------------------------------- | ------ |
| `/auth/login`               | Anmeldung. Redirect auf `?next=…` (whitelisted in-app). | ✅     |
| `/auth/register`            | Registrierung. Leitet auf `/auth/check-email?email=…`.  | ✅     |
| `/auth/check-email`         | Hinweis nach Registrierung.                             | ✅     |
| `/auth/verify-email`        | Bestätigt Token aus E-Mail-Link **per User-Klick**.     | ✅     |
| `/auth/resend-verification` | Fordert neue Bestätigungs-Mail an (immer 202).          | ✅     |

Alle anderen Routen sind durch den Auth-Guard im Root-`+layout.svelte` geschützt: bei `auth.status === 'anonymous'` Redirect auf `/auth/login?next=<aktueller-Pfad>`.

### Verify-Flow: Confirm-Page statt Auto-Submit

Die Verify-E-Mail enthält einen Link auf `/auth/verify-email?token=…`. Die Seite ruft den Endpoint **nicht automatisch** auf, sondern zeigt einen "E-Mail bestätigen"-Button.

**Begründung:**

- E-Mail-Scanner (Outlook Safe-Links, VirusTotal, Antiviren-Gateways) folgen Links beim Empfang und würden den Single-Use-Token aufbrauchen, bevor der User ihn anklicken kann.
- Active-Consent-Pattern entspricht dem DSGVO-Geist (User aktiviert die Verarbeitung selbst).

Der Button ist deaktiviert bei laufender Anfrage; bei Erfolg / Fehler / fehlendem Token rendert die Seite jeweils einen klar getrennten Zustand.

### Module

```
apps/web/src/lib/
├── api/
│   ├── client.ts        # apiFetch + Single-Flight-Refresh + Errors
│   └── auth.ts          # register, login, logout, fetchCurrentUser, verifyEmail, resendVerification
├── stores/
│   └── auth.ts          # AuthState-Store (loading | authenticated | anonymous), hydrate(), login(), logout()
└── components/auth/
    └── PasswordStrength.svelte   # Visueller Strength-Indicator + evaluatePassword()
```

### Fehlerklassen

- `ApiError` — Backend hat geantwortet (Status, parsedes `detail`, Pfad).
- `NetworkError` — Transport-Fehler (offline, CORS, DNS).

Beide sind explizit instanzbar (`err instanceof ApiError`) und ermöglichen status-spezifisches UI-Routing in den Pages.

### Tests

Vitest-Suite (`*.test.ts`) deckt ab:

- `apiFetch`: 2xx/4xx/Network/204, Header-Setting, JSON-Body, **Single-Flight-Refresh** mit 3 Szenarien (Erfolg, Refresh-Fail, parallele Requests).
- Auth-Store: Initialzustand, Hydrate-Transitions, Idempotenz, Login/Logout/setUser.
- Password-Strength: Minimum-Compliance, Score-Steigerung mit Länge/Symbolen.

24 Tests grün (`npm test`).
