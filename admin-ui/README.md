# 🎨 Wine Recommendation Admin UI

Interface web complète pour gérer et visualiser les recommandations du système CRM.

## 🚀 Démarrage Rapide

### Pré-requis
- Node.js 18+
- npm ou yarn

### Installation
```bash
cd admin-ui
npm install
```

### Développement
```bash
npm run dev
```

Accédez à http://localhost:3000

### Build Production
```bash
npm run build
```

The `dist` folder will contain the optimized build.

## 📋 Pages Disponibles

| Page | URL | Description |
|------|-----|-------------|
| **Dashboard** | / | Vue d'ensemble en temps réel |
| **Recommendations** | /recommendations | Recherche et filtrage |
| **Approvals** | /approvals | Gestion des approbations |
| **Quality** | /quality | Métriques de qualité |
| **Compliance** | /compliance | Conformité & gating |
| **Settings** | /settings | Configuration |

## 🏗️ Architecture

```
admin-ui/
├── src/
│   ├── api/           # Client API (Axios)
│   ├── store/         # Global state (Zustand)
│   ├── layouts/       # Layout components
│   ├── pages/         # Page components
│   ├── App.tsx        # Main component
│   └── main.tsx       # Entry point
├── index.html      # HTML file
├── package.json    # Dependencies
├── vite.config.ts  # Vite configuration
├── tsconfig.json   # TypeScript config
└── tailwind.config.ts # Tailwind config
```

## 🗑️ Configuration

### Variables d'environnement

Créez un fichier `.env` :

```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_APP_NAME="Wine Recommendation Admin"
```

### API Configuration

L'API est automatiquement proxifiée via Vite :
- Local: `http://localhost:8000/api/v1`
- Production: Configurable dans `vite.config.ts`

## 📊 Pages Détaillées

### Dashboard
- KPI Cards (4)
- Graphiques de qualité (Couverture, Diversité, Précision)
- Distribution des statuts
- Statistiques récentes

### Recommendations
- Recherche par code client
- Filtrage par scénario
- Filtrage par score minimum
- Affichage en tableau avec barres de progression

### Approvals
- Onglets: Pending / Flagged
- Actions: Approve / Reject / Flag
- Nom de l'approbateur configurable
- Raisons de rejet personnalisées

### Quality
- Métriques globales (7j)
- Sélecteur de run
- Détails du run sélectionné
- Distribution des niveaux de qualité

### Compliance
- Résumé des statuts
- 3 Gating Policies (Strict/Standard/Permissive)
- Logs d'audit récents
- Taux d'approbation
- Score de conformité

### Settings
- Configuration API
- Défaut des recommandations
- Préférences utilisateur
- Thème (Light/Dark/Auto)

## 📄 Tech Stack

- **React 18** - UI Framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Recharts** - Charts & Graphs
- **Zustand** - State management
- **Axios** - HTTP client
- **Vite** - Build tool
- **Lucide Icons** - Icons

## 🚀 Available Scripts

```bash
# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type checking
npm run type-check

# Linting
npm run lint
```

## 📄 API Integration

### Example: Fetching Recommendations

```typescript
import { api } from './api/client'

const recos = await api.getRecommendations('CUST001')
const filtered = await api.getRecommendationsFiltered('CUST001', 'default', 0.5)
```

### Example: Managing Approvals

```typescript
await api.approveRecommendation('audit_123', 'admin', 'Looks good')
await api.rejectRecommendation('audit_123', 'admin', 'Quality too low')
await api.flagRecommendation('audit_123', 'Needs review')
```

### Example: Fetching Quality Metrics

```typescript
const report = await api.getQualityReport(7)
const metrics = await api.getQualityMetrics('run_123')
```

## 📉 State Management (Zustand)

### Using the Store

```typescript
import { useAppStore } from './store'

const App = () => {
  const { currentTab, setCurrentTab, isLoading, error } = useAppStore()

  return (
    <div>
      {error && <div className="text-red-600">{error}</div>}
      {isLoading && <div>Loading...</div>}
    </div>
  )
}
```

## 🌯 Component Structure

### MainLayout
Provides sidebar navigation and header.

```tsx
<MainLayout>
  <Dashboard />
</MainLayout>
```

### Page Components
Each page uses hooks to interact with the store and API:

```tsx
const Dashboard = () => {
  const { setIsLoading, setError } = useAppStore()
  
  useEffect(() => {
    loadData()
  }, [])
}
```

## 🟗️ Styling

All components use Tailwind CSS. Custom colors:
- Primary: `teal-500` (#14b8a6)
- Background: `gray-100` (#f3f4f6)
- Surface: `white` (#ffffff)

## 🔐 Security

- Bearer token authentication
- CORS proxy configuration
- XSS protection (React)
- Secure API endpoints

## 📝 Environment Setup

### Local Development

1. Backend doit tourner sur `http://localhost:8000`
2. Admin UI tourne sur `http://localhost:3000`
3. Proxy Vite redirige `/api` → backend

### Production

Modifier `vite.config.ts` pour pointer vers le vrai backend:

```typescript
proxy: {
  '/api': {
    target: 'https://api.production.com',
    changeOrigin: true,
  },
}
```

## 🤝 Contributing

1. Fork le repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - See LICENSE file

## 📑 Documentation

See [STEP_8_ADMIN_UI.md](../docs/STEP_8_ADMIN_UI.md) for detailed documentation.

---

**Version:** 1.0.0
**Status:** 🟢 Production Ready
**Last Updated:** 2025-12-27
