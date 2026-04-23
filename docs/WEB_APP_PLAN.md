# Claudshi Web — Full Implementation Plan

> A web application that brings Claudshi's political prediction market analysis to the browser, allowing users to scan Kalshi markets, identify mispriced opportunities, analyze them with structured probability frameworks, place bets, and monitor portfolios — all through a polished SaaS interface.

---

## Table of Contents

1. [Product Description](#1-product-description)
2. [Tech Stack](#2-tech-stack)
3. [Architecture](#3-architecture)
4. [Style Guide](#4-style-guide)
5. [Data Model](#5-data-model)
6. [Authentication & Authorization](#6-authentication--authorization)
7. [Billing & Subscriptions](#7-billing--subscriptions)
8. [Page-by-Page Specification](#8-page-by-page-specification)
9. [API Layer](#9-api-layer)
10. [Kalshi Integration](#10-kalshi-integration)
11. [Background Jobs & Monitoring](#11-background-jobs--monitoring)
12. [Risk Engine](#12-risk-engine)
13. [AI Analysis Engine](#13-ai-analysis-engine)
14. [Implementation Plan](#14-implementation-plan)
15. [Testing Strategy](#15-testing-strategy)
16. [Deployment](#16-deployment)
17. [Appendices](#17-appendices)

---

## 1. Product Description

### 1.1 What Is Claudshi Web?

Claudshi Web is a SaaS platform for political event prediction using Kalshi prediction markets. It provides:

- **Market Scanner**: Automatically scans hundreds of political markets to find mispriced opportunities using AI-driven probability estimation.
- **Deep Analysis**: Structured analysis framework that decomposes political events, applies factor analysis, and generates calibrated probability estimates.
- **Portfolio Management**: Real-time portfolio tracking with P&L, exposure metrics, and concentration warnings.
- **Trade Execution**: Place trades on Kalshi with full risk validation, position sizing (quarter-Kelly), and user confirmation flows.
- **Monitoring Dashboard**: Track all positions and watchlist markets with automated alerts for material changes.
- **Journal**: Daily journal entries summarizing positions, actions, and market observations.

### 1.2 Target User

Politically-informed individuals who want data-driven tools for prediction market trading. Users bring their own Kalshi API credentials. The app provides the analytical edge.

### 1.3 Business Model

- **Free Tier**: Read-only market scanning and basic analysis. No trading.
- **Pro Tier** ($29/month or $249/year): Full trading, portfolio tracking, monitoring alerts, unlimited analyses, journal.
- **Users provide their own Kalshi API keys** — Claudshi does not hold user funds or act as a broker.

### 1.4 Core User Flows

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Sign Up   │────▶│  Configure  │────▶│    Scan     │────▶│   Analyze   │
│  (Stripe)   │     │ Kalshi Keys │     │   Markets   │     │   Market    │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                    │
                    ┌─────────────┐     ┌─────────────┐            │
                    │   Monitor   │◀────│    Trade    │◀───────────┘
                    │  Portfolio  │     │  (Confirm)  │
                    └─────────────┘     └─────────────┘
```

---

## 2. Tech Stack

### 2.1 Frontend

| Technology | Purpose | Version |
|------------|---------|---------|
| **Next.js 16** | React framework (App Router) | 16.x |
| **React 19** | UI library | 19.x |
| **TypeScript** | Type safety | 5.x |
| **Tailwind CSS 4** | Utility-first CSS | 4.x |
| **shadcn/ui** | Component library (Radix + Tailwind) | latest |
| **Recharts** | Charts (via shadcn/ui chart components) | 2.x |
| **Tremor** | KPI cards, analytics-specific dashboard components | latest |
| **TanStack Table** | Data tables with sort/filter/paginate (via shadcn/ui) | 8.x |
| **Lucide React** | Icons | latest |
| **Zod** | Schema validation | 3.x |
| **React Hook Form** | Form handling | 7.x |

### 2.2 Backend / Infrastructure

| Technology | Purpose |
|------------|---------|
| **Firebase App Hosting** | Hosting (SSR-capable, Cloud Run-backed) |
| **Firebase Auth** | User authentication (email/password + Google) |
| **Cloud Firestore** | Primary database |
| **Firebase Admin SDK** | Server-side Firebase access |
| **next-firebase-auth-edge** | Auth middleware for App Router / Server Components |

### 2.3 Payments

| Technology | Purpose |
|------------|---------|
| **Stripe** | Subscription billing (Embedded Checkout + Customer Portal) |
| **Stripe Webhooks** | Subscription lifecycle events |

### 2.4 External APIs

| API | Purpose |
|-----|---------|
| **Kalshi API** | Market data, trading, portfolio (user's own credentials) |
| **Claude API (Anthropic)** | AI-powered market analysis and probability estimation |

### 2.5 Development

| Tool | Purpose |
|------|---------|
| **ESLint** | Linting |
| **Prettier** | Code formatting |
| **Vitest** | Unit testing |
| **Playwright** | E2E testing |
| **GitHub Actions** | CI/CD |

### 2.6 Why These Choices

- **Next.js 16 on Firebase App Hosting**: Full SSR support via Cloud Run. Firebase App Hosting is now GA and handles Next.js builds, deploys, and CDN automatically. Cloud Run provides the server runtime. Pay-as-you-go pricing is cost-effective for a startup SaaS.
- **next-firebase-auth-edge**: Enables cookie-based Firebase Auth in Next.js proxy/middleware and Server Components without API routes. Works with the new `proxy.ts` convention in Next.js 16.
- **Firestore over Postgres**: Schema flexibility for evolving market data, built-in real-time listeners for live dashboards, tight Firebase Auth integration, and no server provisioning. Sub-collections map naturally to the existing `.claudshi/` directory structure.
- **shadcn/ui + Tremor**: shadcn/ui for core UI (copy-paste, full customization, minimal bundle). Tremor for KPI cards and analytics-specific components. Both built on Radix + Tailwind, compose well together. TanStack Table (via shadcn/ui) for data-heavy tables with sorting/filtering.
- **Stripe Embedded Checkout**: Renders Stripe-hosted payment form in an iframe on your domain, keeping users on-site while Stripe handles PCI compliance. Preferred over redirect-based Checkout.
- **Stripe Checkout + Customer Portal**: Battle-tested subscription billing with minimal custom UI. Customers manage their own billing via Stripe-hosted portal.

---

## 3. Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client (Browser)                          │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐  │
│  │  React Client │ │ shadcn/ui     │ │ Recharts (Charts)     │  │
│  │  Components   │ │ Components    │ │                       │  │
│  └───────┬───────┘ └───────────────┘ └───────────────────────┘  │
│          │                                                       │
│          │  Server Actions / fetch()                             │
└──────────┼───────────────────────────────────────────────────────┘
           │
┌──────────▼───────────────────────────────────────────────────────┐
│                    Next.js App Router (Server)                    │
│                                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ proxy.ts    │  │ Server       │  │ Route Handlers          │ │
│  │ (Auth Gate) │  │ Components   │  │ /api/kalshi/*           │ │
│  │             │  │ (Data Fetch) │  │ /api/stripe/webhook     │ │
│  └─────────────┘  └──────────────┘  │ /api/analysis/*         │ │
│                                      └─────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Server Actions (mutations)                      │ │
│  │  placeTrade(), updateConfig(), addToWatchlist(), etc.        │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────┬──────────────┬──────────────┬────────────────────────┘
            │              │              │
     ┌──────▼──────┐ ┌────▼────┐  ┌──────▼──────┐
     │  Firestore  │ │  Kalshi │  │   Claude    │
     │  (Database) │ │   API   │  │    API      │
     └─────────────┘ └─────────┘  └─────────────┘
            │
     ┌──────▼──────┐
     │   Stripe    │
     │  (Billing)  │
     └─────────────┘
```

### 3.2 Next.js App Router Structure

```
app/
├── (public)/                    # Route group: no auth required
│   ├── layout.tsx               # Public layout (landing page shell)
│   ├── page.tsx                 # Landing page
│   ├── pricing/page.tsx         # Pricing page
│   ├── login/page.tsx           # Login page
│   └── signup/page.tsx          # Signup page
│
├── (app)/                       # Route group: auth required
│   ├── layout.tsx               # App shell (sidebar, header, nav)
│   ├── dashboard/page.tsx       # Dashboard overview
│   ├── scan/page.tsx            # Market scanner
│   ├── market/[ticker]/         # Individual market view
│   │   ├── page.tsx             # Market detail + analysis
│   │   └── trade/page.tsx       # Trade execution
│   ├── portfolio/page.tsx       # Portfolio view
│   ├── watchlist/page.tsx       # Watchlist
│   ├── journal/                 # Journal
│   │   ├── page.tsx             # Journal index (today)
│   │   └── [date]/page.tsx      # Journal entry by date
│   ├── settings/                # Settings
│   │   ├── page.tsx             # General settings (risk config)
│   │   ├── kalshi/page.tsx      # Kalshi API key config
│   │   └── billing/page.tsx     # Stripe billing portal redirect
│   └── monitor/page.tsx         # Monitoring dashboard
│
├── api/                         # Route Handlers
│   ├── kalshi/                  # Kalshi API proxy
│   │   ├── markets/route.ts
│   │   ├── events/route.ts
│   │   ├── orderbook/route.ts
│   │   ├── trade/route.ts
│   │   ├── positions/route.ts
│   │   └── balance/route.ts
│   ├── analysis/
│   │   ├── scan/route.ts        # Run market scan (long-running)
│   │   └── deep/route.ts        # Run deep analysis (long-running)
│   └── stripe/
│       └── webhook/route.ts     # Stripe webhook handler
│
├── proxy.ts                     # Auth middleware (Next.js 16)
├── layout.tsx                   # Root layout
└── globals.css                  # Tailwind global styles
```

### 3.3 Component Architecture

```
components/
├── ui/                          # shadcn/ui primitives (auto-generated)
│   ├── button.tsx
│   ├── card.tsx
│   ├── table.tsx
│   ├── dialog.tsx
│   ├── chart.tsx
│   ├── badge.tsx
│   ├── input.tsx
│   ├── select.tsx
│   ├── tabs.tsx
│   ├── toast.tsx
│   ├── skeleton.tsx
│   └── ...
│
├── layout/                      # App shell components
│   ├── sidebar.tsx              # Main sidebar nav
│   ├── header.tsx               # Top bar (user menu, notifications)
│   └── mobile-nav.tsx           # Mobile navigation
│
├── market/                      # Market-related components
│   ├── market-card.tsx          # Market summary card (for scanner)
│   ├── market-detail.tsx        # Full market detail view
│   ├── orderbook.tsx            # Live orderbook display
│   ├── price-chart.tsx          # Candlestick / line chart
│   ├── factor-table.tsx         # Factor analysis table
│   ├── probability-badge.tsx    # Probability display with edge
│   └── trade-form.tsx           # Trade confirmation form
│
├── portfolio/                   # Portfolio components
│   ├── position-table.tsx       # Positions table with P&L
│   ├── portfolio-summary.tsx    # Aggregate metrics cards
│   ├── balance-chart.tsx        # Portfolio value over time
│   └── exposure-chart.tsx       # Exposure breakdown donut
│
├── analysis/                    # Analysis components
│   ├── analysis-card.tsx        # Analysis summary card
│   ├── analysis-detail.tsx      # Full analysis markdown view
│   ├── edge-indicator.tsx       # Visual edge indicator
│   └── recommendation-badge.tsx # Trade/Watch/Pass badge
│
├── scan/                        # Scanner components
│   ├── scan-results-table.tsx   # Results table with sorting
│   ├── scan-filters.tsx         # Category and filter controls
│   └── scan-progress.tsx        # Scan progress indicator
│
├── journal/                     # Journal components
│   ├── journal-entry.tsx        # Journal entry display
│   ├── journal-calendar.tsx     # Date picker for journal
│   └── journal-editor.tsx       # Journal composition view
│
└── shared/                      # Shared components
    ├── price-display.tsx        # Formatted price display ($X.XX)
    ├── probability-display.tsx  # Formatted probability (XX.X%)
    ├── edge-display.tsx         # Edge with color coding
    ├── risk-report.tsx          # Risk check results display
    ├── loading-skeleton.tsx     # Page-level loading skeletons
    ├── error-boundary.tsx       # Error boundary wrapper
    └── empty-state.tsx          # Empty state illustrations
```

### 3.4 Server vs Client Component Strategy

**Server Components** (default — no `"use client"` directive):
- All page components that fetch data
- Layout components
- Static display components (market detail, analysis view, journal entries)
- Components that read from Firestore via Admin SDK

**Client Components** (`"use client"` directive):
- Interactive charts (Recharts requires client)
- Forms (trade form, settings, login)
- Real-time data (Firestore onSnapshot listeners)
- Orderbook display (auto-refreshing)
- Toast notifications
- Modal dialogs
- Filter/sort controls

---

## 4. Style Guide

### 4.1 Design Principles

1. **Information-dense but scannable**: Trading dashboards need to show lots of data. Use clear visual hierarchy and consistent spacing.
2. **Data-first**: Numbers, probabilities, and prices are the hero. Make them large, well-formatted, and color-coded.
3. **Minimal chrome**: Reduce decorative elements. Let the data speak. Use whitespace strategically.
4. **Dark mode default**: Financial/trading apps conventionally use dark themes. Support light mode as secondary.
5. **Status through color**: Green = profit/bullish/pass, Red = loss/bearish/fail, Yellow = warning, Blue = informational.

### 4.2 Color Palette

```
/* Dark theme (default) */
--background:          hsl(224, 20%, 6%)      /* Near-black with blue tint */
--foreground:          hsl(210, 20%, 95%)     /* Off-white */

--card:                hsl(224, 18%, 10%)     /* Slightly elevated surface */
--card-foreground:     hsl(210, 20%, 95%)

--muted:               hsl(224, 15%, 16%)     /* Subtle backgrounds */
--muted-foreground:    hsl(220, 10%, 55%)     /* Deemphasized text */

--primary:             hsl(217, 91%, 60%)     /* Bright blue — primary actions */
--primary-foreground:  hsl(0, 0%, 100%)

--accent:              hsl(262, 80%, 60%)     /* Purple — brand accent */
--accent-foreground:   hsl(0, 0%, 100%)

--destructive:         hsl(0, 84%, 60%)       /* Red — errors, losses */
--destructive-foreground: hsl(0, 0%, 100%)

/* Semantic colors */
--profit:              hsl(142, 76%, 46%)     /* Green — gains, bullish */
--loss:                hsl(0, 84%, 60%)       /* Red — losses, bearish */
--warning:             hsl(38, 92%, 50%)      /* Amber — caution */
--edge-positive:       hsl(142, 76%, 46%)     /* Green — positive edge */
--edge-negative:       hsl(0, 84%, 60%)       /* Red — negative edge */
--confidence-high:     hsl(142, 76%, 46%)
--confidence-medium:   hsl(38, 92%, 50%)
--confidence-low:      hsl(0, 84%, 60%)
```

### 4.3 Typography

```
/* Font stack */
font-family: 'Inter', system-ui, -apple-system, sans-serif;

/* Monospace for numbers and prices */
font-family-mono: 'JetBrains Mono', 'Fira Code', monospace;

/* Scale */
--text-xs:   0.75rem  / 1rem      /* Labels, timestamps */
--text-sm:   0.875rem / 1.25rem   /* Table data, secondary text */
--text-base: 1rem     / 1.5rem    /* Body text */
--text-lg:   1.125rem / 1.75rem   /* Section headers */
--text-xl:   1.25rem  / 1.75rem   /* Page section titles */
--text-2xl:  1.5rem   / 2rem      /* Page titles */
--text-3xl:  1.875rem / 2.25rem   /* Hero numbers (P&L, probabilities) */
--text-4xl:  2.25rem  / 2.5rem    /* Landing page headings */
```

**Rules:**
- All monetary values and probabilities use `font-mono` for alignment.
- Prices display as `$X.XX` with 2 decimal places.
- Probabilities display as `XX.X%` with 1 decimal place.
- Edge values show sign: `+12.3%` or `-5.7%`.
- Profit values are green, losses are red.

### 4.4 Layout Grid

- **Sidebar**: 256px fixed width (collapsible to 64px icon-only on desktop, drawer on mobile).
- **Main content**: Fluid, max-width 1440px, centered with `px-6` padding.
- **Card grid**: 1 column on mobile, 2 on tablet, 3-4 on desktop. Use `gap-4` or `gap-6`.
- **Tables**: Full-width within cards. Horizontal scroll on mobile.
- **Minimum tap target**: 44x44px for all interactive elements.

### 4.5 Component Styling Rules

- **Cards**: `rounded-lg border bg-card p-6`. No shadow by default (dark mode). Subtle border.
- **Tables**: Striped rows (`even:bg-muted/50`). Fixed header. Right-align numeric columns.
- **Buttons**: Primary (blue), Secondary (outline), Destructive (red), Ghost (text-only).
- **Badges**: Solid background for status (green/red/yellow). Outlined for categories.
- **Charts**: Use consistent color palette. Grid lines subtle (`stroke-muted`). Tooltip on hover.
- **Loading states**: Skeleton placeholders matching the layout shape. Never empty flicker.
- **Empty states**: Centered illustration + heading + action button. Never a blank page.

### 4.6 Iconography

Use **Lucide React** icons consistently:
- `TrendingUp` / `TrendingDown` for market direction
- `DollarSign` for monetary values
- `BarChart3` for analysis
- `Search` for scanner
- `Briefcase` for portfolio
- `Eye` for watchlist
- `BookOpen` for journal
- `Settings` for config
- `LogOut` / `LogIn` for auth
- `AlertTriangle` for warnings
- `CheckCircle` / `XCircle` for pass/fail
- `ArrowUpRight` / `ArrowDownRight` for positive/negative changes

---

## 5. Data Model

### 5.1 Firestore Collection Structure

The Firestore schema mirrors the existing `.claudshi/` file system but adapted for multi-user, multi-document access patterns.

```
firestore/
├── users/{uid}                          # User profile & settings
│   ├── kalshiApiKey: string (encrypted) # Encrypted Kalshi API key
│   ├── kalshiPrivateKey: string (enc.)  # Encrypted Kalshi private key
│   ├── plan: "free" | "pro"
│   ├── stripeCustomerId: string
│   ├── stripeSubscriptionId: string
│   ├── subscriptionStatus: string
│   ├── config: {                        # Risk config (same as current config.yaml)
│   │   max_single_bet_usd: number,
│   │   max_position_usd: number,
│   │   max_portfolio_exposure_usd: number,
│   │   min_edge_pct: number,
│   │   confidence_threshold: number,
│   │   monitor_interval_hours: number,
│   │   categories: string[]
│   │ }
│   ├── createdAt: timestamp
│   └── updatedAt: timestamp
│
├── users/{uid}/portfolio/summary         # Single doc: portfolio summary
│   ├── cash_cents: number
│   ├── portfolio_value_cents: number
│   ├── total_invested_cents: number
│   ├── total_unrealized_pnl_cents: number
│   ├── num_positions: number
│   └── updatedAt: timestamp
│
├── users/{uid}/portfolio/balanceLog/{id} # Balance snapshots
│   ├── timestamp: timestamp
│   ├── balance_cents: number
│   └── portfolio_value_cents: number
│
├── users/{uid}/positions/{ticker}        # Open positions
│   ├── ticker: string
│   ├── event_slug: string
│   ├── side: "YES" | "NO"
│   ├── quantity: number
│   ├── avg_price_cents: number
│   ├── total_cost_cents: number
│   ├── current_price_cents: number
│   ├── current_value_cents: number
│   ├── unrealized_pnl_cents: number
│   ├── openedAt: timestamp
│   └── updatedAt: timestamp
│
├── users/{uid}/watchlist/{ticker}        # Watched markets
│   ├── ticker: string
│   ├── title: string
│   ├── event_slug: string
│   ├── last_price_cents: number
│   ├── estimated_edge_pct: number
│   ├── recommended_side: "YES" | "NO"
│   ├── claude_probability: number
│   └── addedAt: timestamp
│
├── users/{uid}/analyses/{id}             # All analyses
│   ├── ticker: string
│   ├── event_slug: string
│   ├── title: string
│   ├── type: "initial" | "update"
│   ├── date: string (YYYY-MM-DD)
│   ├── yes_probability: number
│   ├── confidence: "low" | "medium" | "high"
│   ├── edge_pct: number
│   ├── recommendation: "trade" | "watch" | "pass"
│   ├── factors: Array<{name, score, reasoning}>
│   ├── content_md: string               # Full markdown analysis
│   ├── market_price_at_analysis: number
│   └── createdAt: timestamp
│
├── users/{uid}/trades/{id}               # Trade history
│   ├── ticker: string
│   ├── event_slug: string
│   ├── side: "YES" | "NO"
│   ├── action: "buy" | "sell"
│   ├── quantity: number
│   ├── price_cents: number
│   ├── cost_cents: number
│   ├── order_type: "limit"
│   ├── order_id: string
│   ├── status: "filled" | "resting" | "partial"
│   └── createdAt: timestamp
│
├── users/{uid}/journal/{date}            # Journal entries (YYYY-MM-DD)
│   ├── date: string
│   ├── content_md: string
│   ├── positions_snapshot: object
│   └── createdAt: timestamp
│
├── users/{uid}/events/{slug}             # Event metadata cache
│   ├── event_ticker: string
│   ├── title: string
│   ├── category: string
│   └── updatedAt: timestamp
│
└── users/{uid}/events/{slug}/markets/{ticker}  # Market metadata cache
    ├── ticker: string
    ├── title: string
    ├── expiration_time: string
    ├── last_price_cents: number
    ├── volume: number
    ├── status: string
    └── updatedAt: timestamp
```

### 5.2 Firestore Security Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only access their own data
    match /users/{uid}/{document=**} {
      allow read, write: if request.auth != null && request.auth.uid == uid;
    }
  }
}
```

### 5.3 Encryption

Kalshi API keys are sensitive and must not be stored in plaintext. Use server-side encryption:

- Encrypt with AES-256-GCM using a key from Google Cloud KMS (or a Firebase environment secret).
- Store the encrypted blob + IV in Firestore.
- Decrypt only on the server (Route Handlers / Server Actions) when making Kalshi API calls.
- Never send decrypted keys to the client.

---

## 6. Authentication & Authorization

### 6.1 Auth Flow

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  Client   │────▶│  Firebase    │────▶│  proxy.ts    │
│  (Login)  │     │  Auth SDK    │     │  (Validate)  │
└──────────┘     └──────────────┘     └──────────────┘
                                              │
                                       ┌──────▼──────┐
                                       │   Server    │
                                       │  Component  │
                                       │ (has user)  │
                                       └─────────────┘
```

### 6.2 Implementation with next-firebase-auth-edge

**proxy.ts** (Next.js 16 — renamed from middleware.ts):

```typescript
import { authMiddleware } from "next-firebase-auth-edge";

export async function proxy(request: NextRequest) {
  return authMiddleware(request, {
    loginPath: "/api/login",
    logoutPath: "/api/logout",
    apiKey: process.env.FIREBASE_API_KEY!,
    cookieName: "AuthToken",
    cookieSignatureKeys: [
      process.env.COOKIE_SECRET_CURRENT!,
      process.env.COOKIE_SECRET_PREVIOUS!,
    ],
    serviceAccount: {
      projectId: process.env.FIREBASE_PROJECT_ID!,
      clientEmail: process.env.FIREBASE_CLIENT_EMAIL!,
      privateKey: process.env.FIREBASE_PRIVATE_KEY!,
    },
    handleValidToken: async ({ token, decodedToken }, headers) => {
      // Allow access to authenticated routes
      return NextResponse.next({ request: { headers } });
    },
    handleInvalidToken: async (reason) => {
      // Redirect to login for app routes
      return NextResponse.redirect(new URL("/login", request.url));
    },
    handleError: async (error) => {
      return NextResponse.redirect(new URL("/login", request.url));
    },
  });
}

export const config = {
  matcher: [
    "/((?!_next|favicon.ico|api/stripe/webhook|pricing).*)",
  ],
};
```

### 6.3 Server Component Auth Access

In Server Components, retrieve the authenticated user via cookies:

```typescript
import { getTokens } from "next-firebase-auth-edge";
import { cookies } from "next/headers";

export default async function DashboardPage() {
  const tokens = await getTokens(await cookies(), {
    apiKey: process.env.FIREBASE_API_KEY!,
    cookieName: "AuthToken",
    cookieSignatureKeys: [/*...*/],
    serviceAccount: {/*...*/},
  });

  if (!tokens) redirect("/login");

  const uid = tokens.decodedToken.uid;
  // Fetch user data from Firestore using Admin SDK
}
```

### 6.4 Auth Providers

- **Email/Password**: Primary signup method.
- **Google OAuth**: Secondary (convenient).
- Future: Apple, GitHub.

---

## 7. Billing & Subscriptions

### 7.1 Stripe Integration Architecture

```
┌─────────────┐  Checkout  ┌─────────────┐  Webhook  ┌─────────────┐
│   Client    │───────────▶│   Stripe    │──────────▶│  Route      │
│  (Buy btn)  │            │  Checkout   │           │  Handler    │
└─────────────┘            └─────────────┘           └──────┬──────┘
                                                            │
                                                     ┌──────▼──────┐
                                                     │  Firestore  │
                                                     │ (update     │
                                                     │  user plan) │
                                                     └─────────────┘
```

### 7.2 Stripe Products

| Product | Price ID | Amount | Interval |
|---------|----------|--------|----------|
| Claudshi Pro Monthly | `price_pro_monthly` | $29 | month |
| Claudshi Pro Annual | `price_pro_annual` | $249 | year |

### 7.3 Checkout Flow (Embedded Checkout)

Use **Stripe Embedded Checkout** (renders in an iframe on your domain, not a redirect):

1. User clicks "Upgrade" on pricing page or settings.
2. Route Handler `POST /api/checkout` creates a Stripe Checkout Session with `ui_mode: 'embedded'` and the user's `stripeCustomerId` (or creates one). Returns `clientSecret`.
3. Client renders `<EmbeddedCheckoutProvider>` + `<EmbeddedCheckout>` from `@stripe/react-stripe-js` using the `clientSecret`.
4. User completes payment within the embedded form (stays on your domain).
5. On success, user is redirected to a return URL. Stripe sends `checkout.session.completed` webhook.
6. Webhook handler updates Firestore: `users/{uid}.plan = "pro"`, sets `subscriptionStatus`.

**Important**: Use `req.text()` (not `req.json()`) in the webhook Route Handler because Stripe signature verification requires the raw body.

### 7.4 Webhook Handler

```
POST /api/stripe/webhook
```

Handle these events:
- `checkout.session.completed` → Activate subscription, set plan to "pro"
- `customer.subscription.updated` → Update subscription status
- `customer.subscription.deleted` → Downgrade to "free"
- `invoice.payment_failed` → Mark subscription as past_due, notify user

### 7.5 Entitlement Checks

```typescript
// lib/entitlements.ts
export type Plan = "free" | "pro";

export const PLAN_LIMITS = {
  free: {
    canTrade: false,
    canAnalyze: true,      // Limited: 3 per day
    canScan: true,          // Limited: 1 per day
    canMonitor: false,
    maxAnalysesPerDay: 3,
    maxScansPerDay: 1,
  },
  pro: {
    canTrade: true,
    canAnalyze: true,
    canScan: true,
    canMonitor: true,
    maxAnalysesPerDay: Infinity,
    maxScansPerDay: Infinity,
  },
} as const;
```

---

## 8. Page-by-Page Specification

### 8.1 Landing Page (`/`)

**Purpose**: Convert visitors to signups.

**Layout**: Full-width, no sidebar. Hero section + feature sections + pricing + CTA.

**Sections**:
1. **Hero**: "AI-Powered Political Prediction Market Analysis" — tagline, CTA button ("Get Started Free"), background with subtle market data visualization.
2. **How It Works**: 3-step flow cards (Scan → Analyze → Trade).
3. **Features**: Grid of feature cards with icons (Scanner, Analysis, Portfolio, Monitoring, Risk Management, Journal).
4. **Live Demo**: Embedded screenshot or animated GIF showing the scanner in action.
5. **Pricing**: Two cards (Free vs Pro) with feature comparison.
6. **CTA**: "Start Finding Mispriced Markets" button.
7. **Footer**: Links, legal, social.

---

### 8.2 Dashboard (`/dashboard`)

**Purpose**: Overview of the user's current state — portfolio health, recent activity, actionable items.

**Layout**: App shell with sidebar. 4-column metric cards at top, charts in middle, activity feed below.

**Components**:

1. **Metric Cards (top row)**:
   - Portfolio Value: `$XXX.XX` with % change
   - Unrealized P&L: `+$XX.XX` (green) or `-$XX.XX` (red)
   - Open Positions: `N` with exposure total
   - Cash Available: `$XXX.XX`

2. **Portfolio Value Chart**: Line chart showing portfolio value over time (from `balanceLog` collection). Default 30-day range with 7d/30d/90d/all toggles.

3. **Position Summary Table**: Compact version of portfolio table (top 5 by P&L impact), with "View All" link to `/portfolio`.

4. **Recent Activity**: Chronological feed of recent actions (trades placed, analyses run, scans completed). Max 10 items.

5. **Watchlist Highlights**: Top 3 watchlist items by edge, with "View All" link.

6. **Quick Actions**: Buttons for "Run Scan", "View Portfolio", "Check Monitor".

**Data Fetching**: Server Component. Reads from Firestore (`portfolio/summary`, latest `balanceLog`, `positions`, `watchlist`, `trades`). Also calls Kalshi `get_balance` for live balance.

---

### 8.3 Market Scanner (`/scan`)

**Purpose**: Scan political prediction markets for mispriced opportunities.

**Layout**: Filter bar at top, results table below, scan progress indicator.

**Components**:

1. **Filter Bar**: Category multi-select (Politics, Elections, World, Economics), minimum edge threshold slider (default 10%), volume minimum input, "Run Scan" button.

2. **Scan Progress**: When scan is running, show a progress bar with status messages ("Fetching events...", "Analyzing 47 markets...", "Estimating probabilities...").

3. **Results Table** (sortable columns):
   | # | Ticker | Market | Price | Vol | Claude Est. | Edge | Side | Actions |
   |---|--------|--------|-------|-----|-------------|------|------|---------|
   | 1 | TICK1  | Will X...| $0.35 | 12K | 48.0% | +13.0% | YES | Analyze / Watch |

4. **Empty State**: "No scan results yet. Click 'Run Scan' to find mispriced markets."

5. **Scan Metadata**: "Scanned 15 events, 47 markets. Found 8 opportunities. Categories: Politics, Elections."

**Behavior**:
- "Run Scan" triggers a Server Action that calls the Kalshi API for events and markets, then calls Claude API for probability estimation.
- Results stream back via Server-Sent Events or polling.
- The scan is the same logic as the existing `/cs_scan` skill (see skill reference).
- Results are saved to the user's watchlist in Firestore.
- "Analyze" button navigates to `/market/[ticker]` and triggers a deep analysis.
- "Watch" button adds to watchlist immediately.

**Plan gate**: Free users get 1 scan/day. Pro users unlimited.

---

### 8.4 Market Detail & Analysis (`/market/[ticker]`)

**Purpose**: Deep dive on a single market — market data, analysis, probability estimate, trade recommendation.

**Layout**: Two-column on desktop. Left column (60%): market info + analysis. Right column (40%): orderbook + trade widget.

**Left Column Components**:

1. **Market Header**: Title, ticker, expiration date, status badge, event breadcrumb.

2. **Price Summary Card**:
   - Last Price: `$0.XX` (large, monospace)
   - Bid/Ask: `$0.XX / $0.XX` with spread
   - 24h Volume: `XX,XXX`
   - Open Interest: `XX,XXX`

3. **Price Chart**: Candlestick or line chart from `get_market_candlesticks`. Time range toggles (1d, 7d, 30d, all).

4. **Analysis Section**:
   - If no analysis exists: "Run Deep Analysis" button (large, primary).
   - If analysis exists: Display the full analysis with sections:
     - **Probability Estimate**: Large badge showing `XX.X%` estimate, confidence level, edge vs market.
     - **Event Decomposition**: What needs to happen for YES.
     - **Base Rate**: Historical frequency.
     - **Factor Analysis Table**: Factors with scores and reasoning.
     - **Recommendation**: Trade / Watch / Pass with reasoning.
     - **Sources**: Links to news articles consulted.
   - "Update Analysis" button to run an incremental update.

5. **Analysis History**: Collapsible list of past analyses with dates and probability trajectory.

**Right Column Components**:

1. **Orderbook**: Real-time bid/ask depth (top 10 levels). Auto-refreshes every 5 seconds. Color-coded (green bids, red asks). Shows total depth at each level.

2. **Trade Widget** (Pro only):
   - Side toggle: YES / NO
   - Amount input (USD)
   - Price input (cents, auto-filled from orderbook)
   - Calculated quantity display
   - Risk summary (inline): max bet check, position check, concentration
   - "Review Trade" button → opens confirmation modal

3. **Our Position** (if exists): Side, quantity, avg price, current P&L, opened date.

**Deep Analysis Flow**:
1. User clicks "Run Deep Analysis".
2. Server Action calls Kalshi API for market data, orderbook, trades, candlesticks.
3. Server Action calls Claude API with the analysis framework prompt.
4. Results stream back (analysis is long — show progress).
5. Analysis saved to Firestore (`analyses` collection).
6. Page re-renders with analysis data.

---

### 8.5 Trade Execution (`/market/[ticker]/trade`)

**Purpose**: Full trade confirmation and execution page.

**Layout**: Single column, centered, max-width 640px. High-signal confirmation flow.

**Components**:

1. **Trade Summary Card**:
   - Market: Title (Ticker)
   - Side: YES / NO
   - Quantity: N contracts
   - Price: XX cents
   - Estimated Cost: $XX.XX
   - Order Type: Limit

2. **Our Analysis Card**:
   - Claude Estimate: XX.X%
   - Market Price: XX.X%
   - Edge: +XX.X%
   - Confidence: medium

3. **Risk Check Results**:
   Each check as a row with pass/fail/warn icon:
   - [PASS] Max single bet: $XX < $50 limit
   - [PASS] Max position: $XX < $200 limit
   - [PASS] Portfolio exposure: $XX < $1000 limit
   - [PASS] Market expiry: 45 days away
   - [WARN] Concentration: 35% (limit 40%)

4. **Portfolio Impact**:
   - Current exposure: $XX.XX → New: $XX.XX
   - Event concentration: XX%

5. **Confirm Button**: Large, red-tinted button: "Confirm Trade — Buy N YES @ $0.XX". Disabled if any hard risk check fails.

6. **Cancel Button**: "Cancel" → back to market page.

**Behavior**:
- Clicking "Confirm Trade" triggers a Server Action that calls `create_order` on Kalshi.
- Show loading spinner during execution.
- On success: display fill details, update Firestore (positions, trades, portfolio), redirect to portfolio.
- On failure: display error, do not update Firestore.

---

### 8.6 Portfolio (`/portfolio`)

**Purpose**: View all open positions, P&L, and portfolio health.

**Layout**: Metric cards at top, positions table, balance chart.

**Components**:

1. **Metric Cards**:
   - Portfolio Value
   - Cash Available
   - Unrealized P&L (with %)
   - Number of Positions

2. **Positions Table** (sortable):
   | Ticker | Side | Qty | Avg Price | Current | Cost | Value | P&L | Weight | Actions |
   |--------|------|-----|-----------|---------|------|-------|-----|--------|---------|
   Clicking a row navigates to `/market/[ticker]`.

3. **Portfolio Value Chart**: Line chart over time.

4. **Exposure Breakdown**: Donut/pie chart showing allocation by event category.

5. **Stale Positions Warning**: If local positions don't match Kalshi, show alert banner.

**Data Fetching**: Server Component fetches live data from Kalshi (`get_balance`, `get_positions`, `get_market` per position) and merges with Firestore data.

---

### 8.7 Watchlist (`/watchlist`)

**Purpose**: Track markets of interest that haven't been traded yet.

**Layout**: Table with action buttons.

**Components**:

1. **Watchlist Table** (sortable):
   | Ticker | Market | Price | Claude Est. | Edge | Side | Added | Actions |
   |--------|--------|-------|-------------|------|------|-------|---------|
   Actions: "Analyze", "Remove", "Trade" (Pro).

2. **Empty State**: "Your watchlist is empty. Run /scan to find opportunities."

3. **Bulk Actions**: "Remove All", "Run Scan to Refresh".

---

### 8.8 Monitor (`/monitor`)

**Purpose**: Check all tracked markets for changes, get actionable recommendations.

**Layout**: Summary at top, per-market cards with change detection.

**Components**:

1. **Run Monitor Button**: "Check All Markets" — triggers monitoring flow.

2. **Monitor Progress**: "Checking 12 positioned markets... Checking 8 watchlist markets..."

3. **Positioned Markets Section**:
   Each market as a card:
   - Header: Ticker + Title
   - Position: YES x50 @ $0.25
   - Price Change: $0.25 → $0.30 (+$0.05)
   - P&L: +$2.50
   - Edge: +8% → +5% (edge decreasing)
   - News: "Senate vote scheduled for next week"
   - **Recommendation Badge**: Hold / Add / Reduce / Exit
   - Action button (if actionable): "Trade" or "Exit Position"

4. **Watchlist Section**: Similar cards but for watched markets.

5. **No Changes Section**: Collapsed list of markets with no material changes.

6. **Journal Note**: "Journal entry saved for today."

---

### 8.9 Journal (`/journal`)

**Purpose**: Daily reflection and tracking.

**Layout**: Calendar sidebar (left), journal content (right).

**Components**:

1. **Date Picker**: Calendar with dots on dates that have entries.
2. **Journal Entry**: Rendered markdown content.
3. **Generate Button**: "Generate Today's Journal" — pulls data from positions, trades, and news to compose an entry via Claude API.
4. **Navigation**: Previous/Next day arrows.

---

### 8.10 Settings (`/settings`)

**Purpose**: Configure risk parameters, Kalshi credentials, and billing.

**Sub-pages**:

#### Settings / General (`/settings`)
- Risk config form (same fields as current `config.yaml`):
  - Max single bet (USD)
  - Max position (USD)
  - Max portfolio exposure (USD)
  - Min edge threshold (%)
  - Confidence threshold
  - Monitor interval (hours)
  - Categories (multi-select)
- "Save" and "Reset Defaults" buttons.

#### Settings / Kalshi (`/settings/kalshi`)
- API Key input (masked, show last 4 chars)
- Private Key upload or paste (stored encrypted)
- "Test Connection" button that calls `get_balance` to verify
- Connection status indicator

#### Settings / Billing (`/settings/billing`)
- Current plan display
- "Manage Subscription" button → redirects to Stripe Customer Portal
- "Upgrade" button (for free users) → Stripe Checkout
- Billing history (from Stripe)

---

## 9. API Layer

### 9.1 Route Handlers (Kalshi Proxy)

All Kalshi API calls go through Next.js Route Handlers so that user API keys never reach the client.

```
GET  /api/kalshi/markets?event_ticker=XXX
GET  /api/kalshi/market?ticker=XXX
GET  /api/kalshi/events?status=open&limit=200
GET  /api/kalshi/orderbook?ticker=XXX
GET  /api/kalshi/trades?ticker=XXX&limit=50
GET  /api/kalshi/candlesticks?ticker=XXX
GET  /api/kalshi/balance
GET  /api/kalshi/positions
POST /api/kalshi/trade          # Place order
DELETE /api/kalshi/order/:id    # Cancel order
GET  /api/kalshi/fills?ticker=XXX
```

Each handler:
1. Authenticates the user (from cookies).
2. Loads the user's encrypted Kalshi credentials from Firestore.
3. Decrypts credentials.
4. Calls the Kalshi API.
5. Returns the response.

### 9.2 Server Actions

For mutations, use Next.js Server Actions:

```typescript
// actions/trade.ts
"use server";
export async function placeTrade(formData: TradeFormData) { /* ... */ }
export async function cancelOrder(orderId: string) { /* ... */ }

// actions/analysis.ts
"use server";
export async function runDeepAnalysis(ticker: string) { /* ... */ }
export async function runMarketScan(categories: string[]) { /* ... */ }

// actions/watchlist.ts
"use server";
export async function addToWatchlist(market: WatchlistEntry) { /* ... */ }
export async function removeFromWatchlist(ticker: string) { /* ... */ }

// actions/config.ts
"use server";
export async function updateConfig(config: Partial<UserConfig>) { /* ... */ }
export async function resetConfig() { /* ... */ }

// actions/journal.ts
"use server";
export async function generateJournal() { /* ... */ }

// actions/monitor.ts
"use server";
export async function runMonitor() { /* ... */ }

// actions/auth.ts
"use server";
export async function saveKalshiCredentials(apiKey: string, privateKey: string) { /* ... */ }
```

### 9.3 Kalshi API Client

Create a reusable Kalshi API client in `lib/kalshi-client.ts`:

```typescript
export class KalshiClient {
  constructor(private apiKey: string, private privateKey: string) {}

  async getEvents(params: GetEventsParams): Promise<Event[]> { /* ... */ }
  async getMarkets(params: GetMarketsParams): Promise<Market[]> { /* ... */ }
  async getMarket(ticker: string): Promise<Market> { /* ... */ }
  async getOrderbook(ticker: string): Promise<Orderbook> { /* ... */ }
  async getTrades(ticker: string, limit?: number): Promise<Trade[]> { /* ... */ }
  async getCandlesticks(ticker: string): Promise<Candlestick[]> { /* ... */ }
  async getBalance(): Promise<Balance> { /* ... */ }
  async getPositions(): Promise<Position[]> { /* ... */ }
  async createOrder(params: CreateOrderParams): Promise<Order> { /* ... */ }
  async cancelOrder(orderId: string): Promise<void> { /* ... */ }
  async getOrders(): Promise<Order[]> { /* ... */ }
  async getFills(ticker?: string): Promise<Fill[]> { /* ... */ }
}
```

**Important Kalshi API notes** (from project memory):
- `get_markets` does NOT accept `status` as a filter param — 400 error. Filter client-side.
- `create_order` ALWAYS use `order_type: "limit"`. Never `"market"` — returns 400.
- Price fields (`last_price_dollars`, `yes_bid_dollars`) are dollar strings (0–1 range), NOT cents.
- `volume_fp`, `position_fp`, `open_interest_fp` are float strings — parse with `parseFloat()`.
- `create_order` params: `ticker`, `side`, `action`, `count`, `order_type`, `yes_price`/`no_price` (cents int).
- Only set the price field matching the side. For YES: set `yes_price`. For NO: set `no_price`.

---

## 10. Kalshi Integration

### 10.1 API Authentication

The Kalshi API uses API key + RSA private key for authentication. The MCP server (kalshi-mcp) handles this in the CLI version. For the web app, we implement it directly:

```typescript
// lib/kalshi-auth.ts
import crypto from "crypto";

export function signRequest(
  privateKeyPem: string,
  timestamp: string,
  method: string,
  path: string
): string {
  const message = `${timestamp}${method}${path}`;
  const sign = crypto.createSign("RSA-SHA256");
  sign.update(message);
  return sign.sign(privateKeyPem, "base64");
}
```

### 10.2 Rate Limiting

Kalshi API has rate limits. Implement client-side rate limiting:
- Max 10 requests/second per user.
- Use a token bucket algorithm.
- Queue requests that exceed the limit.

### 10.3 Data Transformation

Create TypeScript types matching Kalshi API responses and transform functions:

```typescript
// types/kalshi.ts
export interface KalshiMarket {
  ticker: string;
  title: string;
  event_ticker: string;
  status: "active" | "inactive" | "finalized";
  last_price_dollars: string;    // "0.5600"
  yes_bid_dollars: string;
  yes_ask_dollars: string;
  no_bid_dollars: string;
  no_ask_dollars: string;
  volume_fp: string;             // "352983.55"
  volume_24h_fp: string;
  open_interest_fp: string;
  expiration_time: string;       // ISO 8601
  rules_primary: string;
  yes_sub_title: string;
}

// Transform to internal representation
export function toMarket(k: KalshiMarket): Market {
  return {
    ticker: k.ticker,
    title: k.title,
    eventTicker: k.event_ticker,
    status: k.status,
    lastPriceCents: Math.round(parseFloat(k.last_price_dollars) * 100),
    yesBidCents: Math.round(parseFloat(k.yes_bid_dollars) * 100),
    yesAskCents: Math.round(parseFloat(k.yes_ask_dollars) * 100),
    volume: Math.round(parseFloat(k.volume_fp)),
    openInterest: Math.round(parseFloat(k.open_interest_fp)),
    expirationTime: k.expiration_time,
    marketProbability: parseFloat(k.last_price_dollars),
    rulesPrimary: k.rules_primary,
  };
}
```

---

## 11. Background Jobs & Monitoring

### 11.1 Scheduled Market Monitoring

Use Firebase Cloud Functions (2nd gen, Cloud Run-based) or a cron-triggered Route Handler for automated monitoring:

```
Cron Schedule: Every 12 hours (configurable per user)
```

**Option A: Cloud Scheduler + Cloud Function**
- Cloud Scheduler triggers a Cloud Function every hour.
- Function queries Firestore for users whose `monitor_interval_hours` has elapsed since their last monitor run.
- For each due user, run the monitoring flow (same logic as `/cs_monitor`).
- Update Firestore with results.
- Send push notification or email for actionable changes.

**Option B: Client-side polling (simpler, MVP)**
- When user visits `/monitor` or `/dashboard`, check if `monitor_interval_hours` has elapsed since last run.
- Prompt user to "Run Monitor" or auto-trigger.

**Recommendation**: Start with Option B for MVP. Add Option A in a later phase.

### 11.2 Price Alert System (Future)

- User sets alerts: "Notify me if TICKER moves above/below $X.XX"
- Cloud Function checks prices periodically.
- Sends notification (email, push, or in-app).

---

## 12. Risk Engine

### 12.1 TypeScript Port of lib/risk.py

Reimplement the existing Python risk module in TypeScript:

```typescript
// lib/risk.ts

export interface RiskConfig {
  maxSingleBetUsd: number;       // default: 50
  maxPositionUsd: number;        // default: 200
  maxPortfolioExposureUsd: number; // default: 1000
  minEdgePct: number;            // default: 10
  confidenceThreshold: number;   // default: 0.6
  maxConcentrationPct: number;   // default: 40
}

export const DEFAULT_RISK_CONFIG: RiskConfig = {
  maxSingleBetUsd: 50,
  maxPositionUsd: 200,
  maxPortfolioExposureUsd: 1000,
  minEdgePct: 10,
  confidenceThreshold: 0.6,
  maxConcentrationPct: 40,
};

export interface RiskCheckResult {
  name: string;
  passed: boolean;
  severity: "hard" | "warning";
  detail: string;
}

export function checkBet(
  amountUsd: number,
  ticker: string,
  portfolioSummary: PortfolioSummary,
  config: RiskConfig
): RiskCheckResult[] { /* ... */ }

export function checkMarketExpiry(expirationTime: string): RiskCheckResult { /* ... */ }

export function checkConcentration(
  eventSlug: string,
  newAmount: number,
  portfolioSummary: PortfolioSummary,
  config: RiskConfig
): RiskCheckResult { /* ... */ }

export function calculateEdge(
  claudeProbability: number,
  marketProbability: number
): number {
  return (claudeProbability - marketProbability) * 100;
}

export function calculatePositionSize(
  edgePct: number,
  marketProbability: number,
  bankroll: number,
  config: RiskConfig
): number {
  if (edgePct <= 0) return 0;

  const edgeFrac = edgePct / 100;
  const denominator = 1 - edgeFrac;
  const kellyFraction = denominator <= 0
    ? 1.0
    : (edgeFrac * (1 - marketProbability)) / denominator;

  const betSize = Math.max(kellyFraction, 0) * bankroll * 0.25; // quarter-Kelly
  return Math.min(betSize, config.maxSingleBetUsd);
}
```

---

## 13. AI Analysis Engine

### 13.1 Claude API Integration

The analysis engine calls the Claude API (Anthropic) for:
1. **Quick probability estimates** (scanner) — lightweight, fast.
2. **Deep analyses** — full structured analysis framework.
3. **Incremental updates** — delta analysis based on changes.
4. **Journal generation** — summarize the day's activity.

### 13.2 Analysis Prompt Architecture

```typescript
// lib/analysis-prompts.ts

export function buildScanPrompt(markets: MarketForScan[]): string {
  return `You are a political event analyst. For each market below, estimate the
probability of YES resolution. Use base rates, resolution rules, and the provided
news snippets. Return JSON.

Markets:
${markets.map(m => `- ${m.ticker}: ${m.title} (Price: ${m.price}, Rules: ${m.rules})`).join("\n")}

News context:
${newsSnippets}

Return JSON array: [{ ticker, probability, reasoning }]`;
}

export function buildDeepAnalysisPrompt(
  market: MarketDetail,
  news: string[],
  historicalData: string
): string {
  return `You are a political event analyst performing a deep analysis...

## Analysis Framework

### 1. Event Decomposition
- What exactly needs to happen for YES to resolve?
- What is the time window?
- Are there intermediate milestones?

### 2. Base Rate Analysis
- Historical frequency of similar events resolving YES

### 3. Factor Analysis
Rate each on -5 to +5:
- Political will
- Institutional feasibility
- Public pressure
- External forces
- Precedent
- Momentum

### 4. Probability Synthesis
Start from base rate, adjust for factors, calibrate.

### 5. Edge Calculation
Your estimate vs market price of ${market.lastPriceCents}¢

Return your analysis as structured JSON + markdown.`;
}
```

### 13.3 Claude API Client

```typescript
// lib/claude-client.ts
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY!,
});

export async function analyzeMarket(prompt: string): Promise<AnalysisResult> {
  const response = await client.messages.create({
    model: "claude-sonnet-4-5-20250929",
    max_tokens: 4096,
    messages: [{ role: "user", content: prompt }],
  });
  // Parse structured response
  return parseAnalysisResponse(response);
}

export async function quickEstimate(prompt: string): Promise<QuickEstimate[]> {
  const response = await client.messages.create({
    model: "claude-haiku-4-5-20251001", // Faster/cheaper for scan
    max_tokens: 2048,
    messages: [{ role: "user", content: prompt }],
  });
  return parseEstimateResponse(response);
}
```

### 13.4 Web Search Integration

For the analysis to include current news, use a web search API:

**Option A**: SerpAPI or Tavily for programmatic web search.
**Option B**: Claude's tool_use with a web search tool.
**Option C**: Anthropic's built-in web search feature (if available in the API).

The search results are fed into the analysis prompt as context.

---

## 14. Implementation Plan

### Phase 0: Project Setup (Tasks 1-3)

#### Task 1: Initialize Next.js Project
- `npx create-next-app@latest claudshi-web --typescript --tailwind --app --src-dir`
- Configure TypeScript strict mode
- Set up ESLint + Prettier
- Install shadcn/ui: `npx shadcn@latest init`
- Install core dependencies: `zod`, `react-hook-form`, `lucide-react`
- Create `lib/`, `components/`, `types/` directory structure
- Set up environment variables template (`.env.local.example`)
- **Acceptance**: Project runs with `npm run dev`, TypeScript compiles clean

#### Task 2: Firebase Setup
- Create Firebase project in console
- Enable Firebase Auth (email/password + Google)
- Create Firestore database
- Install `firebase`, `firebase-admin`, `next-firebase-auth-edge`
- Configure Firebase Admin SDK with service account
- Write `lib/firebase-admin.ts` (server-side) and `lib/firebase-client.ts` (client-side)
- Write `proxy.ts` with auth middleware
- Create Firestore security rules
- **Acceptance**: Auth middleware protects `/dashboard`, login redirects work

#### Task 3: Stripe Setup
- Create Stripe account and products (Pro Monthly, Pro Annual)
- Install `stripe`
- Write `lib/stripe.ts` — Stripe client initialization
- Create Route Handler: `POST /api/stripe/webhook`
- Handle: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`
- Write `lib/entitlements.ts` — plan checks
- **Acceptance**: Can create checkout session, webhook updates Firestore

---

### Phase 1: Core Infrastructure (Tasks 4-7)

#### Task 4: Data Model & Types
- Define all TypeScript types in `types/`:
  - `types/market.ts` — Market, Event, Orderbook, Trade, Candlestick
  - `types/portfolio.ts` — Position, PortfolioSummary, BalanceEntry
  - `types/analysis.ts` — Analysis, FactorScore, Recommendation
  - `types/user.ts` — UserProfile, UserConfig, Plan
  - `types/kalshi.ts` — Raw Kalshi API response types + transform functions
- Define Zod schemas for form validation
- **Acceptance**: All types compile, transform functions have unit tests

#### Task 5: Kalshi API Client
- Implement `lib/kalshi-client.ts` with all methods
- Implement `lib/kalshi-auth.ts` for RSA signature
- Implement `lib/kalshi-crypto.ts` for credential encryption/decryption
- Write Route Handlers: all `/api/kalshi/*` endpoints
- Add rate limiting
- **Acceptance**: Can fetch markets, positions, balance through route handlers. Unit tests for auth signing.

#### Task 6: Risk Engine
- Port `lib/risk.py` to `lib/risk.ts`
- All functions: `checkBet`, `checkMarketExpiry`, `checkConcentration`, `calculateEdge`, `calculatePositionSize`
- **Acceptance**: All risk functions have comprehensive unit tests, matching Python behavior

#### Task 7: Firestore Data Layer
- Create `lib/firestore/` with data access functions:
  - `lib/firestore/users.ts` — user CRUD, config
  - `lib/firestore/portfolio.ts` — portfolio summary, balance log, positions
  - `lib/firestore/watchlist.ts` — watchlist CRUD
  - `lib/firestore/analyses.ts` — analysis CRUD
  - `lib/firestore/trades.ts` — trade log
  - `lib/firestore/journal.ts` — journal entries
  - `lib/firestore/events.ts` — event/market metadata cache
- Each module exports typed functions using Firebase Admin SDK
- **Acceptance**: Can create, read, update all Firestore collections. Integration tests pass.

---

### Phase 2: UI Shell & Auth (Tasks 8-11)

#### Task 8: App Shell Layout
- Build `(app)/layout.tsx` — sidebar + main content area
- Build `components/layout/sidebar.tsx` — navigation links, user menu, collapsible
- Build `components/layout/header.tsx` — breadcrumbs, notification bell, user avatar
- Build `components/layout/mobile-nav.tsx` — mobile drawer
- Responsive: sidebar collapses to icons at md breakpoint, drawer on mobile
- **Acceptance**: Navigation works on all breakpoints, sidebar highlights active route

#### Task 9: Auth Pages
- Build `/login` page — email/password form + Google sign-in button
- Build `/signup` page — email/password form + Google sign-in button + Terms checkbox
- Build auth client utilities — `useAuth` hook, sign-in/sign-up/sign-out functions
- Login/signup forms use React Hook Form + Zod validation
- On successful signup, create user document in Firestore with defaults
- **Acceptance**: Can sign up, log in, log out. Auth state persists across page loads.

#### Task 10: Landing Page
- Build `/` landing page with sections: Hero, How It Works, Features, Pricing, CTA, Footer
- Responsive design
- "Get Started" buttons link to `/signup`
- Pricing cards show Free vs Pro comparison
- **Acceptance**: Page renders correctly on mobile and desktop, CTAs link properly

#### Task 11: Settings Pages
- Build `/settings` — risk config form with save/reset
- Build `/settings/kalshi` — API key entry, private key entry, test connection
- Build `/settings/billing` — current plan, upgrade/manage buttons
- Kalshi credential save → encrypts and stores in Firestore
- "Test Connection" calls `get_balance` and shows result
- Billing "Upgrade" → creates Stripe Checkout session and redirects
- Billing "Manage" → redirects to Stripe Customer Portal
- **Acceptance**: Can save/load config, save encrypted Kalshi keys, test connection, subscribe via Stripe

---

### Phase 3: Core Features (Tasks 12-17)

#### Task 12: Dashboard
- Build `/dashboard` page with metric cards, portfolio chart, position summary, recent activity, quick actions
- Fetch live balance from Kalshi + Firestore data
- Portfolio value chart from `balanceLog`
- **Acceptance**: Dashboard shows live data, charts render, responsive layout

#### Task 13: Portfolio Page
- Build `/portfolio` page with full positions table, metric cards, charts
- Fetch live data from Kalshi (`get_balance`, `get_positions`, `get_market` per position)
- Calculate P&L per position and totals
- Save portfolio snapshot to Firestore
- Detect stale positions (local vs Kalshi mismatch)
- **Acceptance**: Portfolio shows all positions with live P&L, sorting works, stale positions detected

#### Task 14: Market Scanner
- Build `/scan` page with filter bar, results table, scan progress
- Implement scan Server Action:
  1. Fetch events from Kalshi
  2. Fetch markets per event, filter for active/liquid
  3. Call Claude API for quick probability estimates
  4. Calculate edge, rank results
  5. Save to watchlist
- Stream progress updates to client
- **Acceptance**: Scan finds markets, displays ranked results, saves to watchlist, respects plan limits

#### Task 15: Market Detail & Analysis
- Build `/market/[ticker]` page with two-column layout
- Price summary, price chart, orderbook, position display
- "Run Deep Analysis" button triggers analysis Server Action:
  1. Fetch all market data from Kalshi
  2. Web search for latest news
  3. Call Claude API with deep analysis prompt
  4. Parse structured response
  5. Save analysis to Firestore
  6. Re-render page with results
- Display analysis with all framework sections
- Analysis history timeline
- **Acceptance**: Full analysis workflow completes, results display correctly, saved to Firestore

#### Task 16: Trade Execution
- Build `/market/[ticker]/trade` page with confirmation flow
- Pre-fill from orderbook and analysis data
- Run all risk checks client-side for instant feedback + server-side for enforcement
- Confirmation button calls `placeTrade` Server Action
- Server Action: validate risks, call `create_order`, poll `get_fills`, update Firestore
- Success: show fill details, redirect to portfolio
- Failure: show error, no Firestore update
- **Acceptance**: Can place limit orders (YES and NO), fills confirmed, positions updated, risk checks enforced

#### Task 17: Watchlist
- Build `/watchlist` page with table and action buttons
- "Analyze" navigates to market page and triggers analysis
- "Remove" removes from watchlist
- "Trade" navigates to trade page (Pro only)
- **Acceptance**: Watchlist displays, CRUD operations work, plan gating enforced

---

### Phase 4: Advanced Features (Tasks 18-21)

#### Task 18: Monitor Dashboard
- Build `/monitor` page with "Run Monitor" flow
- Monitor Server Action:
  1. Load all positioned and watched markets
  2. Fetch latest prices from Kalshi
  3. Search for news via web search
  4. Call Claude API for incremental analysis updates
  5. Determine recommended actions (Hold/Add/Reduce/Exit/Enter)
  6. Save updated analyses and journal entry to Firestore
- Display per-market cards with recommendations
- **Acceptance**: Monitor detects price changes, generates recommendations, saves analysis updates

#### Task 19: Journal
- Build `/journal` page with calendar sidebar and entry display
- Build `/journal/[date]` page for specific date
- "Generate Today's Journal" Server Action:
  1. Pull positions, trades, and market data
  2. Call Claude API to compose journal entry
  3. Save to Firestore
- Render markdown content
- **Acceptance**: Can generate and view journal entries, calendar shows dates with entries

#### Task 20: Exit Position Flow
- Add "Exit Position" action to portfolio and market pages
- Build exit confirmation modal/page:
  - Full exit: close entire position
  - Partial exit: specify amount
  - Show realized P&L calculation
  - Require confirmation
- Execute via `create_order` (sell action, opposite side)
- Update Firestore (position, trades, portfolio)
- **Acceptance**: Can fully and partially exit positions, P&L calculated correctly

#### Task 21: Real-time Updates
Use a **hybrid real-time strategy**:

**Server-Sent Events (SSE) for market data** — one-way server-to-client streams. SSE is ideal for market data because it works with serverless (Cloud Run), auto-reconnects, and is simpler than WebSockets for one-directional data:
- Create `GET /api/market-stream?tickers=X,Y,Z` Route Handler that polls Kalshi and streams price updates
- Orderbook updates on market detail page (every 5s)
- Position price updates on portfolio page (every 30s)

**Firestore `onSnapshot` for user data** — real-time from the database:
- Portfolio summary (live P&L after trade execution)
- Trade status (fill confirmations)
- Analysis completion notifications

**Client-side implementation:**
- `usePriceStream(tickers)` hook using `EventSource` API
- `usePortfolio(uid)` hook using Firestore `onSnapshot`
- React context or Zustand for client-side state management
- **Acceptance**: Price changes reflect without page reload, orderbook auto-updates, trade fills appear in real-time

---

### Phase 5: Polish & Launch (Tasks 22-26)

#### Task 22: Error Handling & Edge Cases
- Global error boundary component
- API error handling: Kalshi down, rate limited, invalid credentials
- Firestore error handling: permission denied, offline
- Form validation with clear error messages
- Loading skeletons for all async content
- Empty states for all lists/tables
- **Acceptance**: No unhandled errors, graceful degradation, clear user feedback

#### Task 23: Mobile Responsiveness
- Test and fix all pages on mobile viewports
- Touch-friendly tap targets (44px minimum)
- Collapsible tables → card layout on mobile
- Swipe gestures where appropriate
- **Acceptance**: All pages usable on 375px viewport

#### Task 24: Testing
- Unit tests (Vitest):
  - Risk engine (port existing Python tests)
  - Data transformations
  - Kalshi auth signing
  - Entitlement checks
- Integration tests:
  - Firestore data layer
  - Stripe webhook handling
- E2E tests (Playwright):
  - Signup → configure → scan → analyze → trade → portfolio flow
  - Login/logout
  - Plan upgrade flow
- **Acceptance**: >80% coverage on core logic, E2E happy paths pass

#### Task 25: Performance & SEO
- Implement ISR for landing page
- Add `loading.tsx` skeletons for all routes
- Optimize images (next/image)
- Add meta tags, Open Graph, Twitter cards
- Lighthouse score >90 on landing page
- **Acceptance**: Landing page loads in <2s, Lighthouse >90

#### Task 26: Deployment & CI/CD
- Configure Firebase App Hosting:
  - `firebase.json` with App Hosting config
  - `apphosting.yaml` for build settings
  - Environment variables in Firebase console
- Set up GitHub Actions:
  - Lint + type check on PR
  - Run tests on PR
  - Deploy to preview on PR
  - Deploy to production on merge to main
- Configure custom domain
- Set up monitoring (Firebase Performance, error tracking)
- **Acceptance**: App deployed and accessible, CI/CD pipeline runs, preview deploys work

---

## 15. Testing Strategy

### 15.1 Test Pyramid

```
        ╱╲
       ╱ E2E ╲          5-10 tests (Playwright)
      ╱────────╲         Critical user flows
     ╱Integration╲       15-20 tests (Vitest)
    ╱──────────────╲      Firestore, API, Stripe
   ╱   Unit Tests   ╲    50+ tests (Vitest)
  ╱──────────────────╲    Risk, transforms, utils
```

### 15.2 Key Test Scenarios

**Unit Tests:**
- Risk checks: all pass, each individual failure, edge cases (zero edge, negative, 100% edge)
- Kelly sizing: various edge/probability combinations
- Kalshi data transforms: dollar strings → cents, float strings → numbers
- Entitlement checks: free vs pro feature access
- Price formatting: cents → display, probability → percentage

**Integration Tests:**
- Firestore: create user → save config → read config
- Firestore: save analysis → list analyses → get by ticker
- Stripe webhook: simulate `checkout.session.completed` → verify Firestore updated
- Kalshi proxy: mock Kalshi API → verify route handler response

**E2E Tests:**
- Full flow: signup → settings → scan → market → trade → portfolio
- Auth: login, logout, protected route redirect
- Billing: upgrade flow (Stripe test mode)

---

## 16. Deployment

### 16.1 Firebase App Hosting Configuration

**`apphosting.yaml`:**
```yaml
runConfig:
  minInstances: 0
  maxInstances: 10
  cpu: 1
  memoryMiB: 512
  concurrency: 80

env:
  - variable: FIREBASE_API_KEY
    secret: FIREBASE_API_KEY
  - variable: FIREBASE_PROJECT_ID
    value: claudshi-web
  - variable: ANTHROPIC_API_KEY
    secret: ANTHROPIC_API_KEY
  - variable: STRIPE_SECRET_KEY
    secret: STRIPE_SECRET_KEY
  - variable: STRIPE_WEBHOOK_SECRET
    secret: STRIPE_WEBHOOK_SECRET
  - variable: COOKIE_SECRET_CURRENT
    secret: COOKIE_SECRET_CURRENT
  - variable: COOKIE_SECRET_PREVIOUS
    secret: COOKIE_SECRET_PREVIOUS
  - variable: ENCRYPTION_KEY
    secret: ENCRYPTION_KEY
```

**`firebase.json`:**
```json
{
  "hosting": {
    "source": ".",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"]
  }
}
```

### 16.2 Environment Variables

| Variable | Description | Where |
|----------|-------------|-------|
| `FIREBASE_API_KEY` | Firebase Web API key | Firebase Console |
| `FIREBASE_PROJECT_ID` | Firebase project ID | Firebase Console |
| `FIREBASE_CLIENT_EMAIL` | Service account email | Firebase Console |
| `FIREBASE_PRIVATE_KEY` | Service account private key | Secret Manager |
| `ANTHROPIC_API_KEY` | Claude API key | Anthropic Console |
| `STRIPE_SECRET_KEY` | Stripe secret key | Stripe Dashboard |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | Stripe Dashboard |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | Stripe Dashboard |
| `STRIPE_PRICE_MONTHLY` | Stripe price ID for monthly | Stripe Dashboard |
| `STRIPE_PRICE_ANNUAL` | Stripe price ID for annual | Stripe Dashboard |
| `COOKIE_SECRET_CURRENT` | Cookie signing key (current) | Generate |
| `COOKIE_SECRET_PREVIOUS` | Cookie signing key (previous) | Generate |
| `ENCRYPTION_KEY` | AES-256 key for Kalshi credential encryption | Generate |

### 16.3 CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22 }
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm run test
```

---

## 17. Appendices

### 17.1 Existing Claudshi Functionality Reference

The web app reimplements the following existing Claudshi CLI skills:

| CLI Skill | Web App Equivalent |
|-----------|-------------------|
| `/cs_config` | Settings page (`/settings`) |
| `/cs_analyze` | Market detail page analysis button (`/market/[ticker]`) |
| `/cs_scan` | Scanner page (`/scan`) |
| `/cs_bet` | Trade execution page (`/market/[ticker]/trade`) |
| `/cs_portfolio` | Portfolio page (`/portfolio`) |
| `/cs_monitor` | Monitor page (`/monitor`) |
| `/cs_exit` | Exit action on portfolio/market pages |
| `/cs_journal` | Journal page (`/journal`) |

### 17.2 Existing Python Library Reference

| Python Module | TypeScript Port |
|--------------|----------------|
| `lib/memory.py` | `lib/firestore/*.ts` (file system → Firestore) |
| `lib/risk.py` | `lib/risk.ts` (direct port) |
| `lib/formatting.py` | `components/shared/*.tsx` (React components instead of markdown strings) |

### 17.3 Kalshi API Quick Reference

```
Base URL: https://api.elections.kalshi.com/trade-api/v2

GET  /events                     # List events
GET  /events/{event_ticker}      # Event detail
GET  /markets                    # List markets (filter by event_ticker)
GET  /markets/{ticker}           # Market detail
GET  /markets/{ticker}/orderbook # Orderbook
GET  /markets/trades             # Recent trades
GET  /markets/{ticker}/candlesticks # OHLCV
GET  /portfolio/balance          # Account balance
GET  /portfolio/positions        # Open positions
POST /portfolio/orders           # Create order
DELETE /portfolio/orders/{id}    # Cancel order
GET  /portfolio/fills            # Fill history
```

### 17.4 File/Directory Structure (Final)

```
claudshi-web/
├── app/
│   ├── (public)/                # Public routes (no auth)
│   │   ├── layout.tsx
│   │   ├── page.tsx             # Landing
│   │   ├── pricing/page.tsx
│   │   ├── login/page.tsx
│   │   └── signup/page.tsx
│   ├── (app)/                   # Authenticated routes
│   │   ├── layout.tsx           # App shell
│   │   ├── dashboard/page.tsx
│   │   ├── scan/page.tsx
│   │   ├── market/[ticker]/
│   │   │   ├── page.tsx
│   │   │   └── trade/page.tsx
│   │   ├── portfolio/page.tsx
│   │   ├── watchlist/page.tsx
│   │   ├── monitor/page.tsx
│   │   ├── journal/
│   │   │   ├── page.tsx
│   │   │   └── [date]/page.tsx
│   │   └── settings/
│   │       ├── page.tsx
│   │       ├── kalshi/page.tsx
│   │       └── billing/page.tsx
│   ├── api/
│   │   ├── kalshi/
│   │   │   ├── markets/route.ts
│   │   │   ├── events/route.ts
│   │   │   ├── orderbook/route.ts
│   │   │   ├── trade/route.ts
│   │   │   ├── positions/route.ts
│   │   │   └── balance/route.ts
│   │   ├── analysis/
│   │   │   ├── scan/route.ts
│   │   │   └── deep/route.ts
│   │   └── stripe/
│   │       └── webhook/route.ts
│   ├── proxy.ts
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── ui/                      # shadcn/ui
│   ├── layout/
│   ├── market/
│   ├── portfolio/
│   ├── analysis/
│   ├── scan/
│   ├── journal/
│   └── shared/
├── lib/
│   ├── firebase-admin.ts
│   ├── firebase-client.ts
│   ├── stripe.ts
│   ├── kalshi-client.ts
│   ├── kalshi-auth.ts
│   ├── kalshi-crypto.ts
│   ├── claude-client.ts
│   ├── analysis-prompts.ts
│   ├── risk.ts
│   ├── entitlements.ts
│   ├── utils.ts
│   └── firestore/
│       ├── users.ts
│       ├── portfolio.ts
│       ├── watchlist.ts
│       ├── analyses.ts
│       ├── trades.ts
│       ├── journal.ts
│       └── events.ts
├── actions/
│   ├── trade.ts
│   ├── analysis.ts
│   ├── watchlist.ts
│   ├── config.ts
│   ├── journal.ts
│   ├── monitor.ts
│   └── auth.ts
├── types/
│   ├── market.ts
│   ├── portfolio.ts
│   ├── analysis.ts
│   ├── user.ts
│   └── kalshi.ts
├── tests/
│   ├── unit/
│   │   ├── risk.test.ts
│   │   ├── transforms.test.ts
│   │   └── entitlements.test.ts
│   ├── integration/
│   │   ├── firestore.test.ts
│   │   └── stripe-webhook.test.ts
│   └── e2e/
│       ├── auth.spec.ts
│       ├── scan.spec.ts
│       └── trade.spec.ts
├── public/
│   ├── favicon.ico
│   └── og-image.png
├── firebase.json
├── apphosting.yaml
├── firestore.rules
├── .env.local.example
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── README.md
```

### 17.5 Task Dependency Graph

```
Phase 0: Setup
  Task 1: Init Next.js ──┐
  Task 2: Firebase ───────┼──┐
  Task 3: Stripe ─────────┘  │
                              │
Phase 1: Infrastructure       │
  Task 4: Types ◀─────────────┘
  Task 5: Kalshi Client ◀── Task 4
  Task 6: Risk Engine ◀──── Task 4
  Task 7: Firestore Layer ◀─ Task 4
                              │
Phase 2: UI Shell             │
  Task 8: App Shell ◀────────┘
  Task 9: Auth Pages ◀──── Task 8
  Task 10: Landing Page ◀── Task 8
  Task 11: Settings ◀────── Task 8, 5, 7
                              │
Phase 3: Core Features        │
  Task 12: Dashboard ◀──── Task 7, 8, 5
  Task 13: Portfolio ◀───── Task 5, 6, 7, 8
  Task 14: Scanner ◀──────── Task 5, 6, 7, 8, 13*
  Task 15: Market Detail ◀── Task 5, 7, 8, 13*
  Task 16: Trade Exec ◀──── Task 5, 6, 7, 15
  Task 17: Watchlist ◀────── Task 7, 8
                              │
Phase 4: Advanced             │
  Task 18: Monitor ◀──────── Task 15, 13
  Task 19: Journal ◀──────── Task 7, 8, 13
  Task 20: Exit Position ◀── Task 16
  Task 21: Real-time ◀────── Task 13, 15
                              │
Phase 5: Polish               │
  Task 22: Error Handling ◀── All above
  Task 23: Mobile ◀────────── All above
  Task 24: Testing ◀────────── All above
  Task 25: Performance ◀───── All above
  Task 26: Deployment ◀────── All above

* 13 = Claude API integration (analysis prompts)
```

---

*Document version: 1.0*
*Created: 2026-04-23*
*Last updated: 2026-04-23*
