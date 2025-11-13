# Dara Local Server - Launch Instructions

## ✅ All Issues Resolved (v1.1.2hw_v0.3)

### Fixed Issues:
1. ✅ **UV Dependency Conflict** - Platform-specific Ray versions configured
2. ✅ **UI Localization** - All Chinese text replaced with English
3. ✅ **Tutorial Updated** - Comprehensive guide for local database search
4. ✅ **Windows Compatibility** - Removed emoji from launch script

### Launch the Backend Server

Simply run:

```powershell
cd D:\Haiwen\Code_Repositories\dara
uv run python launch_local_server.py
```

The server will start on **http://localhost:8899**

### Features Available:

- **Local Database Support**: COD, ICSD, MP databases
- **Chemical System Filtering**: Filter by required/excluded elements
- **Custom CIF Uploads**: Add your own structure files
- **New Search Interface**: `/search` page with English UI
- **Original Interface**: `/` (legacy reaction predictor)

### Verify UI Changes:

1. Open browser to http://localhost:8899/search
2. You should see:
   - "Local Database Phase Search" (title)
   - "Required Elements" (form label)
   - "Exclude Elements (Optional)" (form label)
   - All UI text in English

### Tutorial:

Visit http://localhost:8899/tutorial to see the updated guide explaining:
- How to use required elements (typically sufficient)
- When to use exclude elements (usually not needed)
- Subsystem auto-inclusion behavior

### Database Paths:

The server expects index files at:
- COD: `indexes/cod_index.parquet` / `cod_cifs/`
- ICSD: `indexes/icsd_index.parquet` / `icsd_cifs/`
- MP: `indexes/mp_index.parquet` / `mp_cifs/`

### Notes:

- Ant Design library still contains some Chinese for calendar/pagination (non-critical)
- All user-facing business logic text is in English
- Tutorial comprehensively rewritten
- Python 3.11-3.12 required (Ray compatibility)

---

**Ready to use!** 🎉

Last updated: Version 1.1.2hw_v0.3
