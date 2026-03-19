# 🎯 DEMO vs MAIN APP - QUICK REFERENCE

## 📊 Comparison Table

| Aspect | Main App | Standalone Demo |
|--------|----------|----------------|
| **Entry Point** | `index.html` | `demo.html` |
| **JS Entry** | `src/main.jsx` → `App.jsx` | `src/main-demo.jsx` → `DemoApp.jsx` |
| **Bundle Size** | ~904 KB | ~22 KB (97% lighter!) |
| **Database** | ✅ Supabase | ❌ None (mock data) |
| **Auth** | ✅ Real login | ✅ Quick login (mock) |
| **Data Source** | ✅ Database | ✅ `src/demoData.js` |
| **Dependencies** | Full (Supabase, XLSX, etc) | Minimal (React, Router, Swal) |
| **Pages** | 21 pages | 2 pages (Login, Dashboard) |
| **Env Vars** | Required (Supabase) | ❌ Not required |
| **Impact** | Production | Zero impact |
| **URL** | `exam.smkn1rongga.sch.id` | `demo.exam.smkn1rongga.sch.id/demo.html` |

## 🚀 Quick Commands

```bash
# Development
npm run dev              # Main app (localhost:5173)
npm run dev:demo         # Demo app (localhost:5173/demo.html)

# Build
npm run build            # Build both (main + demo)

# Preview
npm run preview          # Preview main
npm run preview:demo     # Preview demo
```

## 📂 Key Files

### Demo-Specific Files
```
src/
├── demoData.js                    # Mock data
├── DemoApp.jsx                    # Demo router
├── main-demo.jsx                  # Demo entry
└── pages/
    ├── StandaloneDemoLogin.jsx    # Demo login
    └── DemoDashboard.jsx          # Demo dashboard

demo.html                          # Demo HTML
```

### Shared Files
```
src/
├── App.css                        # Styles
└── assets/
    └── logo_sekolah.png           # Logo

vite.config.js                     # Multi-entry build
package.json                       # Scripts
```

### Main App Files (NOT used by demo)
```
src/
├── supabaseClient.js              # ❌ NOT imported by demo
├── App.jsx                        # ❌ Main app only
├── main.jsx                       # ❌ Main app only
└── pages/
    ├── Login.jsx                  # ❌ Main app only
    ├── Dashboard.jsx              # ❌ Main app only
    └── ... 19 other pages         # ❌ Main app only
```

## 🔐 GitHub Secrets

### Main App Deployment
```
# FTP
FTP_SERVER
FTP_USERNAME
FTP_PASSWORD

# Supabase
VITE_SUPABASE_URL
VITE_SUPABASE_ANON_KEY
```

### Demo Deployment
```
# FTP only!
DEMO_FTP_SERVER
DEMO_FTP_USERNAME
DEMO_FTP_PASSWORD

# NO Supabase vars needed!
```

## 🎮 User Experience

### Main App
1. Visit `exam.smkn1rongga.sch.id`
2. Login dengan Email/NIS + Password
3. Database query
4. Full features (21 pages)

### Demo
1. Visit `demo.exam.smkn1rongga.sch.id/demo.html`
2. Click role button (no password)
3. Mock data loaded
4. Dashboard simulasi (2 pages)

## 🔒 Security & Isolation

### Main App
- Connected to Supabase
- Real database access
- Production data
- User authentication
- Full features

### Demo
- ✅ NO database connection
- ✅ NO Supabase import
- ✅ NO API calls
- ✅ Mock data only
- ✅ Separate session flag (`isDemoMode: true`)
- ✅ Cannot affect main app
- ✅ Cannot access production data

## 📈 Build Output

```
dist/
├── index.html              # Main app entry
├── demo.html               # Demo entry
└── assets/
    ├── main-*.js          # 904 KB - full app
    ├── main-*.css         # 74 KB
    ├── demo-*.js          # 22 KB - demo only
    ├── demo-*.css         # 0.5 KB
    └── logo_sekolah-*.js  # Shared image
```

## 🎯 Use Cases

### Main App
- ✅ Production usage
- ✅ Real exams
- ✅ Data management
- ✅ Student/teacher operations
- ✅ Full CBT system

### Demo
- ✅ Presentations
- ✅ UI/UX demos
- ✅ Stakeholder previews
- ✅ Training material
- ✅ Marketing
- ❌ NOT for production
- ❌ NOT for real exams

## 💡 Key Points

### Main App
- Full-featured CBT system
- Database-driven
- Production-ready
- 21 pages with complex features
- Requires Supabase setup

### Demo
- Lightweight showcase
- Mock data driven
- Presentation-ready
- 2 pages with simulated features
- No setup required (except FTP)
- **100% isolated from main app**
- **ZERO database dependency**
- **Cannot harm production**

## 🚨 Important Notes

1. **Demo NEVER connects to database**
   - All data is hardcoded in `src/demoData.js`
   - No Supabase client imported
   - No API calls made

2. **Separate builds**
   - Different HTML entry points
   - Different JS bundles
   - No runtime code sharing

3. **Session isolation**
   - Demo: `{ ..., isDemoMode: true }`
   - Main: No `isDemoMode` flag
   - Apps reject each other's sessions

4. **Deployment isolation**
   - Different domains/subdomains
   - Different FTP targets
   - Different workflows

## ✅ Verification Checklist

### Main App
- [ ] Connects to Supabase ✅
- [ ] Uses real database ✅
- [ ] Requires credentials ✅
- [ ] Full feature set ✅
- [ ] Production data ✅

### Demo
- [ ] NO Supabase connection ✅
- [ ] NO database queries ✅
- [ ] Mock data only ✅
- [ ] Quick login ✅
- [ ] Isolated build ✅
- [ ] Cannot affect main app ✅

---

**Last Updated:** 2026-03-19
**Version:** 2.0.0 (Standalone Demo)
