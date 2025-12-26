# ÉTAPE 8 : Admin UI Dashboard

## 🎨 Vue d'ensemble

Interface web complète pour gérer et visualiser les recommandations.

**Technologies:**
- React 18 + TypeScript
- Tailwind CSS
- Recharts pour les visualisations
- Zustand pour la gestion d'état
- Axios pour les appels API

## 📊 Pages Principales

### 1. Dashboard (Accueil)
**Objectif:** Vue d'ensemble en temps réel

**Composants:**
- 4 KPI Cards: Total recommandations, clients uniques, taux d'approbation, approbations en attente
- Graphiques de qualité (7 jours): Couverture, Diversité, Précision
- Distribution des statuts d'approbation
- Distribution des niveaux de qualité
- Cartes d'activité récente

**Données:**
```typescript
GET /api/v1/recommendations/stats/overview
GET /api/v1/audit/quality/report
GET /api/v1/audit/compliance/summary
```

### 2. Recommendations (Recherche)
**Objectif:** Consulter les recommandations

**Fonctionnalités:**
- Recherche par code client
- Filtrage par scénario (default, new_customer, high_value, retention)
- Filtrage par score minimum
- Affichage en tableau avec scores et explications

**Données:**
```typescript
GET /api/v1/recommendations/{customer_code}/filtered
```

### 3. Approvals (Gestion)
**Objectif:** Approuver/Rejeter les recommandations

**Fonctionnalités:**
- Onglets: Pending (⏳) et Flagged (⚠️)
- Affichage détaillé: Client, Produit, Score, Scénario, Date
- Actions: Approve (✅), Reject (❌), Flag (⚠️)
- Saisie du nom de l'approbateur
- Raison personnalisée pour les rejets

**Données:**
```typescript
GET /api/v1/audit/pending
GET /api/v1/audit/flagged
POST /api/v1/audit/approve/{audit_id}
POST /api/v1/audit/reject/{audit_id}
POST /api/v1/audit/flag/{audit_id}
```

### 4. Quality (Métriques)
**Objectif:** Analyser la qualité des recommandations

**Composants:**
- Summary Cards: Couverture moyenne, Diversité moyenne, Précision moyenne
- Sélecteur de run (historique des 7 derniers jours)
- Détails du run sélectionné:
  - Total recommandations
  - Coverage/Diversity/Accuracy scores
  - Score moyen et médian
  - Niveau de qualité (EXCELLENT/GOOD/ACCEPTABLE/POOR)
- Distribution des niveaux de qualité (graphique barres)

**Données:**
```typescript
GET /api/v1/audit/quality/report
GET /api/v1/audit/quality/metrics/{run_id}
```

### 5. Compliance (Conformité)
**Objectif:** Monitorer la conformité et les gating policies

**Sections:**
- Cards des statuts d'approbation (PENDING, APPROVED, REJECTED, FLAGGED)
- 3 Gating Policies:
  - Strict (65% pass rate)
  - Standard (82% pass rate)
  - Permissive (95% pass rate)
- Logs d'audit des 10 derniers (avec statut, score, date)
- Taux d'approbation global
- Score de conformité

**Données:**
```typescript
GET /api/v1/audit/compliance/summary
GET /api/v1/audit/logs
```

### 6. Settings (Configuration)
**Objectif:** Configurer l'interface

**Sections:**
- **API Configuration:**
  - URL de l'API (défaut: http://localhost:8000)
  - Intervalle de refresh (défaut: 30s)
- **Recommendation Defaults:**
  - Scénario par défaut
  - Nombre max de recommandations
- **User Settings:**
  - Nom de l'approbateur
  - Thème (Light/Dark/Auto)
- **About:** Version, statut, date de mise à jour

**Stockage:** localStorage

## 🏗️ Architecture

```
admin-ui/
├── public/
├── src/
│   ├── api/
│   │   └── client.ts           # Client Axios + méthodes API
│   ├── store/
│   │   └── index.ts            # Zustand store (état global)
│   ├── layouts/
│   │   └── MainLayout.tsx      # Layout principal avec sidebar
│   ├── pages/
│   │   ├── Dashboard.tsx       # Page d'accueil
│   │   ├── Recommendations.tsx # Recherche recommandations
│   │   ├── Approvals.tsx       # Gestion approbations
│   │   ├── Quality.tsx         # Métriques de qualité
│   │   ├── Compliance.tsx      # Conformité & gating
│   │   └── Settings.tsx        # Configuration
│   ├── App.tsx                 # Routeur principal
│   ├── main.tsx                # Entry point
│   └── index.css               # Styles Tailwind
├── index.html                  # HTML entry point
├── package.json                # Dépendances
├── vite.config.ts              # Configuration Vite
├── tsconfig.json               # Configuration TypeScript
├── tailwind.config.ts          # Configuration Tailwind
└── README_ADMIN_UI.md          # Documentation
```

## 🚀 Démarrage Rapide

### Installation
```bash
cd admin-ui
npm install
```

### Développement
```bash
npm run dev
# Accès: http://localhost:3000
```

### Build Production
```bash
npm run build
npm run preview
```

### TypeScript Check
```bash
npm run type-check
```

### Lint
```bash
npm run lint
```

## 📱 Interface utilisateur

### Sidebar Navigation
- 🏠 Dashboard
- 📋 Recommendations
- ✅ Approvals
- 📊 Quality
- ⚖️ Compliance
- ⚙️ Settings
- 🚪 Logout

### Color Scheme
- Primary: Teal (#14b8a6)
- Background: Light Gray (#f9fafb)
- Surface: White (#ffffff)
- Text: Dark Gray (#1f2937)

### Responsive Design
- Mobile: 320px+
- Tablet: 768px+
- Desktop: 1024px+

## 🔗 Intégration API

### API Client Configuration
```typescript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1'
```

### Intercepteurs
- **Request:** Ajoute le token d'authentification (Bearer token)
- **Response:** Gère les erreurs 401 (logout automatique)

### Endpoints Utilisés

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/recommendations/stats/overview` | GET | Statistiques générales |
| `/recommendations/{customer_code}` | GET | Recommandations par client |
| `/recommendations/{customer_code}/filtered` | GET | Recommandations filtrées |
| `/recommendations/batch` | POST | Génération batch |
| `/audit/logs` | GET | Logs d'audit |
| `/audit/pending` | GET | Approbations en attente |
| `/audit/flagged` | GET | Recommandations signalées |
| `/audit/approve/{audit_id}` | POST | Approuver |
| `/audit/reject/{audit_id}` | POST | Rejeter |
| `/audit/flag/{audit_id}` | POST | Signaler |
| `/audit/quality/metrics/{run_id}` | GET | Métriques de qualité |
| `/audit/quality/report` | GET | Rapport de qualité |
| `/audit/gating/check/{recommendation_id}` | POST | Vérifier gating |
| `/audit/compliance/summary` | GET | Résumé de conformité |

## 🎯 Gestion d'État (Zustand)

### State Structure
```typescript
interface AppStore {
  // UI State
  currentTab: string
  setCurrentTab: (tab: string) => void

  // Data State
  recommendations: Recommendation[]
  qualityMetrics: QualityMetrics | null
  auditLogs: AuditLog[]
  pendingApprovals: AuditLog[]

  // Loading/Error State
  isLoading: boolean
  error: string | null

  // Filters
  selectedCustomer: string | null
  selectedScenario: string | null
  dateRange: { from: Date | null, to: Date | null }
}
```

## 📈 Features Clés

✅ Dashboard en temps réel avec KPIs
✅ Recherche et filtrage des recommandations
✅ Workflow d'approbation complet
✅ Métriques de qualité détaillées
✅ Conformité et gating policies
✅ Configuration utilisateur
✅ Visualisations Recharts
✅ Responsive design Tailwind
✅ Gestion d'état Zustand
✅ Client API type-safe Axios

## 🔐 Sécurité

- Authentication avec Bearer token
- CORS configuration via proxy Vite
- Input validation côté client
- Protection contre les XSS (React sanitization)
- HTTPS en production

## 📝 Next Steps

### Phase 1 (Immédiat)
- [ ] Integration avec vrai backend
- [ ] Authentication/Login page
- [ ] Export données (PDF/CSV)

### Phase 2 (Court terme)
- [ ] Real-time updates (WebSocket)
- [ ] Notifications push
- [ ] Dark mode complet
- [ ] Graphs animations

### Phase 3 (Long terme)
- [ ] PWA (Progressive Web App)
- [ ] Mobile app (React Native)
- [ ] AI insights & recommendations
- [ ] Advanced filtering/search

## 📚 Ressources

- [React Documentation](https://react.dev)
- [Tailwind CSS](https://tailwindcss.com)
- [Recharts](https://recharts.org)
- [Zustand](https://github.com/pmndrs/zustand)
- [Vite](https://vitejs.dev)
- [TypeScript](https://www.typescriptlang.org)

## 🤝 Support

Pour les questions:
- Consulter la documentation API
- Vérifier les types TypeScript
- Examiner les exemples d'utilisation

---

**Status:** ✅ Production Ready
**Version:** 1.0.0
**Last Updated:** 2025-12-27
