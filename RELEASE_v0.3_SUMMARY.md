# v1.1.2hw_v0.3 Release Summary

**Release Date**: November 13, 2025  
**Tag**: 1.1.2hw_v0.3  
**Commit**: 71ea2f0

---

## 🎯 Release Highlights

### Major Updates
1. **Complete UI Localization** - All Chinese text replaced with English
2. **Interactive Tutorial** - Step-by-step guide at `/search-tutorial`
3. **Documentation Cleanup** - README.md completely rewritten
4. **Bug Fixes** - Web UI loading, Ray compatibility, import paths

### Files Modified in This Release Session (Nov 13, 2025)

#### Source Code
- `src/dara_local/server/ui/src/pages/search.js` - Added tutorial link, English labels
- `src/dara_local/server/ui/src/pages/index.js` - Updated banner to English
- `src/dara_local/server/ui/src/md-pages/tutorial.md` - Comprehensive rewrite
- `src/dara_local/server/ui/src/md-pages/search-tutorial.md` - New tutorial page
- `launch_local_server.py` - Removed emoji for Windows compatibility
- `pyproject.toml` - Platform-specific Ray dependencies

#### Built Files (UI)
- `src/dara_local/server/ui/public/search/index.html` - English text
- `src/dara_local/server/ui/public/search-tutorial/index.html` - Tutorial page (standalone)
- `src/dara_local/server/ui/public/component---src-pages-*.js` - Updated components
- `src/dara_local/server/ui/public/index.html` - Updated banner
- `src/dara_local/server/ui/package.json` - Simplified for Windows

#### Documentation
- `README.md` - Complete rewrite with clean structure
- `CHANGELOG.md` - Added v0.3 UI updates section
- `LAUNCH_INSTRUCTIONS.md` - New comprehensive guide
- `README_v0.3_before_cleanup.md` - Backup of previous README

---

## 📋 Commit History (Recent)

```
71ea2f0 - docs: Clean up and finalize v1.1.2hw_v0.3 documentation
f9801b6 - fix: Create built HTML for search-tutorial page
b04f516 - feat: Add local database search tutorial link and page
fd7d793 - docs: Add launch instructions for v1.1.2hw_v0.3
fec7267 - fix: Remove emoji from launch script for Windows compatibility
72b8d00 - fix: Replace all Chinese text in UI with English (built files)
a41c6f7 - build: Update built UI with English translations
843bb96 - build: Simplify package.json scripts for Windows compatibility
c510887 - docs: Remove Chinese text and update tutorial for new search
add5b32 - fix: Platform-specific Ray version in strict dependencies
```

---

## 🐛 Bug Fixes

### Critical Issues Resolved
1. **Web UI Loading Spinner** - Fixed infinite loading when displaying task results
2. **Chemical Formula Display** - All CIF entries now show "Formula (ID)" format
3. **Ray Compatibility** - Platform-specific versions (Windows: 2.50.1, Others: 2.51.x)
4. **Python Version Lock** - Restricted to 3.11-3.12 for Ray compatibility
5. **Import Path Issues** - Fixed `database_interface` module imports
6. **Windows Console Encoding** - Removed emoji characters causing UnicodeEncodeError
7. **Gatsby Build** - Created workaround with standalone HTML pages

---

## ✨ New Features

### UI Enhancements
- **English Localization**: All user-facing text now in English
- **Tutorial Link**: "📖 How to Use (Tutorial)" on search page
- **Improved Labels**: Clear form labels and helpful tooltips
- **Search Tutorial Page**: Interactive guide at `/search-tutorial`

### Documentation
- **README.md**: Complete rewrite with:
  - Quick Start guide
  - Two web interfaces comparison
  - Troubleshooting section
  - Database setup instructions
  - System requirements
- **LAUNCH_INSTRUCTIONS.md**: Detailed launch guide
- **Tutorial.md**: Rewritten with new search workflow
- **Search Tutorial**: Standalone HTML page

---

## 📊 Statistics

- **Total Commits**: 11 (in v0.3 session)
- **Files Modified**: 20+
- **Lines Added**: ~3000
- **Lines Removed**: ~200
- **Documentation**: 4 major files updated/created

---

## 🚀 Quick Start (After This Release)

```bash
# Clone and setup
git clone https://github.com/harvey-dai-haiwen/dara_hw.git
cd dara_hw
uv sync

# Launch server
uv run python launch_local_server.py

# Access
# Main interface: http://localhost:8899/search
# Tutorial: http://localhost:8899/search-tutorial
```

---

## 🔍 What Changed from v0.2

### v0.2 → v0.3 Changes
| Aspect | v0.2 | v0.3 |
|--------|------|------|
| UI Language | Mixed (Chinese + English) | Full English |
| Tutorial | Legacy only | Interactive + Legacy |
| Windows Support | Partial | Full (emoji fix) |
| Documentation | Mixed README | Clean structure |
| Ray Version | Generic | Platform-specific |
| Build Process | Gatsby required | Workaround added |

---

## ⚠️ Breaking Changes

None. All changes are backwards compatible.

---

## 🧪 Testing Checklist

- [x] Server starts successfully
- [x] UI displays in English
- [x] Tutorial link works
- [x] Search page loads
- [x] Task submission works
- [x] Results display correctly
- [x] Chemical formulas show properly
- [x] No console encoding errors (Windows)
- [x] Ray imports successfully
- [x] All dependencies install via `uv sync`

---

## 📝 Known Issues

1. **Gatsby Build**: Original build process still hangs - workaround with standalone HTML works
2. **Ant Design i18n**: Some UI library text remains in Chinese (calendar, pagination) - non-critical

---

## 🎓 Tutorial Content

The new `/search-tutorial` page includes:

### Step-by-Step Workflow
0. Username entry
1. XRD file upload (supported formats)
2. Database selection (COD/ICSD/MP)
3. Element specification (required vs excluded)
4. Parameter configuration
5. Task submission

### Results Interpretation
- Task status tracking
- Phase identification guide
- Rwp value explanation
- Visualization controls
- Multiple solutions comparison

### Pro Tips
- Typically only specify required elements
- Database selection strategy
- Element syntax examples
- Multi-solution analysis

---

## 🤝 Contributors

- **Harvey Dai** (harvey-dai-haiwen) - All v0.3 updates
- **Original Dara Team** - Base framework

---

## 📜 License

Rights reserved by original developers of Dara and databases.

---

**End of Release Summary**

For detailed changelog, see `CHANGELOG.md`  
For usage instructions, see `README.md`  
For launch guide, see `LAUNCH_INSTRUCTIONS.md`
