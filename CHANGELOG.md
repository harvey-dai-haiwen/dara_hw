# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.2hw_v0.3] - 2025-11-13

### Fixed
- **Web UI Loading Bug**: Fixed infinite loading spinner when displaying task results
  - Moved return statement outside for loop in `/api/task/{task_id}` endpoint
  - Added proper None handling for `final_result` and `predict_kwargs`
  - Fixed COD numeric filename parsing in compositional clustering
- **UI Localization**: Removed all Chinese text from web interface
  - Replaced Chinese labels with English in search page
  - Updated index page banner to English
  - Fixed Windows console emoji encoding issues in launch script
- **Gatsby Build Issues**: Bypassed problematic build process
  - Created standalone HTML pages for tutorial
  - Direct text replacement in built files as workaround
  - Simplified package.json scripts for Windows compatibility
- **Chemical Formula Display**: All CIF entries now show "Formula (ID)" format
  - Example: "Y4Mo4O11 (281037)" instead of just "281037"
  - Applied to all result fields: final_result.phases, highlighted_phases, grouped_phases
  - Uses pymatgen Structure parsing to extract Composition.reduced_formula
- **Ray Compatibility**: Platform-specific dependency configuration
  - Windows: `ray>=2.10.0,<2.51.0` (tested with 2.50.1)
  - Linux/macOS: `ray>=2.51.0`
  - Fixes "no Windows wheels available" error for Ray 2.51.x
- **Python Version Lock**: Restricted to 3.11-3.12
  - Python 3.13 not compatible with Ray on Windows
  - Updated environment setup instructions
- **Import Path Issues**: Fixed `database_interface` module import
  - Added fallback import mechanism in `scripts/dara_adapter.py`
  - Works correctly in both script and package contexts

### Added
- **Search Tutorial Page**: Interactive guide for local database search
  - Step-by-step workflow (username → file upload → database → elements → submit)
  - File format documentation (xy, txt, xye, xrdml, raw)
  - Database selection guide (MP, ICSD, COD)
  - Element filtering explained with examples (Ge Te → finds Ge, Te, GeTe, not GeO2)
  - Results interpretation guide (Rwp, phase identification, visualization)
  - Accessible at `/search-tutorial` with link from search page
- **Launch Instructions**: Comprehensive guide in `LAUNCH_INSTRUCTIONS.md`
  - Server startup commands
  - Feature overview
  - UI verification steps
  - Database path requirements
- **Tutorial Updates**: Complete rewrite of tutorial.md
  - Added "NEW: Local Database Search (Recommended)" section
  - Explained required vs excluded elements behavior
  - Documented subsystem auto-inclusion (unary/binary/ternary)
  - Marked original interface as "Legacy"
- **Comprehensive README**: Complete rewrite for v0.3 release
  - Quick start guide with UV package manager
  - Two web interface comparison (port 8899 vs 8898)
  - Troubleshooting section with common issues and solutions
  - Database rebuild instructions
  - Backup of previous README as `README_v0.2_backup.md`
- **Production Validation**: Full fresh clone testing workflow
  - Verified installation from scratch
  - Tested all dependencies including Ray 2.50.1
  - Validated server startup and API responses
  - Confirmed chemical formula display in results

### Changed
- **Version Tag**: Updated from `v0.1.0` to `1.1.2hw_v0.3` for consistency
- **Documentation Focus**: Shifted emphasis to new local web server (port 8899)
- **Git Workflow**: Created backup before release (`dara_backup_20251113_105207`)

### Technical Details
- Fixed 5 separate bugs in `src/dara_local/server/api_router.py`
- Total changes: 1016 insertions, 153 deletions across 4 files
- Validated with 100% test success rate in fresh environment

---

## [1.1.2+hw_v0.2] - 2025-11-10

### Fixed
- **UV Environment**: Ensured all dependencies work out-of-the-box with `uv sync`
  - Explicitly declared `pyarrow>=22.0.0` for parquet database support
  - Verified all 27 critical dependencies (numpy, pandas, pymatgen, ray, etc.)
  - Added `verify_dependencies.py` script for installation verification

### Added
- **UV Setup Guide**: Comprehensive `UV_SETUP_GUIDE.md` for one-command environment setup
  - Quick start instructions for Windows/macOS/Linux
  - Troubleshooting guide for common issues
  - CI/CD integration examples
  - Migration guide from conda/pip

### Changed
- **Version format**: Changed from `1.1.2hw` to `1.1.2+hw` (PEP 440 local version identifier)
- **Documentation**: Improved dependency management documentation

---

## [1.1.2hw] - 2025-10-30

This is a hardware-lab tailored fork aligned to the original Dara 1.1.x line for version consistency. It includes documentation and workflow improvements without changing core public APIs.

### Added
- Streamlined phase analysis notebook (`notebooks/streamlined_phase_analysis.ipynb`) with exportable reports
- Database helper scripts:
  - `scripts/setup_databases.ps1` (one-shot ICSD/COD/MP setup on Windows)
  - `scripts/check_data_status.py` (index and CIF folder sanity check)
- Environment bootstrap guide (`docs/environment_setup.md`)
- Full-refresh database guide (`docs/database_update.md`)

### Changed
- README restructured to make 3.0-style Quick Start primary, with Advanced section for full-refresh indexing
- `.gitignore` hardened to exclude all CIFs and index directories by default
- Preserved legacy landing page as `README_original.md`

### Notes
- Package version set to `1.1.2hw` for lab-local distribution; if publishing to PyPI, consider a distinct package name to avoid conflicts with upstream
- Large datasets (CIF folders and indexes) are intentionally not tracked in Git

## [3.0.0] - 2025-10-29

### 🎉 Major Features

#### Materials Project (MP) Database Integration
- **New**: Complete MP indexing with 169,385 crystal structures
- **New**: Automatic experimental/theoretical classification
  * 59,936 experimental structures (35.4%) — identified via `database_IDs` field
  * 109,449 theoretical structures (64.6%) — DFT-computed structures
- **New**: Thermodynamic stability filtering via `energy_above_hull` field
- **New**: Structure → CIF conversion for all MP entries (100% success rate)
- **New**: 100% data completeness (spacegroup, CIF path, energy data)

### ✨ Enhanced Features

#### Unified Database Interface
- **Added**: `database_interface.py` - single API for ICSD, COD, and MP
- **Added**: `filter_by_experimental_status()` - filter experimental vs theoretical structures
- **Added**: `filter_by_stability()` - filter by thermodynamic stability (eV/atom)
- **Improved**: Element filtering with required/optional/excluded modes
- **Improved**: Multi-format support (parquet, sqlite, json.gz)

#### DARA Adapter
- **Updated**: `dara_adapter.py` with MP-specific parameters:
  * `experimental_only: bool` - restrict to experimental structures
  * `include_theoretical: bool` - include DFT-computed structures
  * `max_e_above_hull: float` - stability threshold (eV/atom)
- **Added**: `get_index_stats()` - retrieve index statistics
- **Improved**: Default behavior: MP returns experimental only, ICSD/COD return all

### 🏗️ New Scripts

- `scripts/index_mp.py` - MP index generation from pickle files
- `scripts/verify_mp_index.py` - MP index validation and quality checks
- `scripts/test_pytest_suite.py` - comprehensive test suite (29 tests)

### 📊 Database Statistics

**Total Indexed Structures**: 900,847

| Database | Entries | Spacegroup Coverage | CIF Coverage | Processing Time |
|----------|---------|---------------------|--------------|-----------------|
| ICSD | 229,487 | 97.2% | 100% | ~2.18 hours |
| COD | 501,975 | 98.5% | 100% | ~13.88 hours |
| MP | 169,385 | 100% | 100% | ~9 minutes |
| **merged (ICSD+COD)** | 731,462 | 98.1% | 100% | - |

### 🧪 Testing

- **Added**: Comprehensive pytest suite with 29 tests
  * Basic query tests (6)
  * MP-specific feature tests (6)
  * ICSD/COD behavior tests (3)
  * DARA adapter tests (6)
  * Edge case tests (4)
  * Data integrity tests (4)
- **Result**: 100% test pass rate (29/29)
- **Performance**: All queries < 2 seconds, index loading < 1 second

### 📝 Documentation

- **Updated**: `scripts/README.md` - complete MP integration documentation
- **Updated**: `README.md` - database support overview
- **Added**: `CHANGELOG.md` - version history
- **Added**: Comprehensive usage examples for all three databases

### 🔧 Technical Improvements

- **Fixed**: ICSD CIF extraction from inline CSV data
- **Fixed**: COD spacegroup filling (98.5% coverage achieved)
- **Improved**: Memory efficiency for large-scale indexing
- **Improved**: Error handling and logging

### 🎯 Quality Metrics

- **MP Spacegroup Coverage**: 100% (169,385/169,385)
- **MP CIF Export Success**: 100% (169,385/169,385)
- **MP Energy Data Coverage**: 100% (all entries)
- **Overall Spacegroup Coverage**: 98.6% (887,397/900,847)
- **Overall CIF Path Coverage**: 100% (900,847/900,847)

---

## [2.0.0] - 2024-XX-XX

### Added
- ICSD database indexing
- COD database indexing
- Unified parquet-based index format
- Parallel indexing support
- Spacegroup filling functionality

### Changed
- Migrated from legacy filtering scripts to unified interface
- Improved index merging logic

### Fixed
- Memory leaks in parallel CIF parsing
- Spacegroup extraction edge cases

---

## [1.0.0] - 2023-XX-XX

### Added
- Initial release of DARA
- Automated Rietveld refinement with BGMN
- Phase search functionality
- Web-based interface
- ICSD integration (legacy)

---

## Upgrade Guide

### From 2.x to 3.0

#### New Features
1. **Materials Project Support**: Use `indexes/mp_index.parquet` for MP queries
2. **Experimental/Theoretical Filtering**:
   ```python
   # Old (merged index only)
   db = StructureDatabaseIndex('indexes/merged_index.parquet')
   
   # New (MP with filtering)
   db_mp = StructureDatabaseIndex('indexes/mp_index.parquet')
   experimental = db_mp.filter_by_experimental_status('experimental')
   stable = db_mp.filter_by_stability(max_e_above_hull=0.1)
   ```

3. **DARA Adapter Parameters**:
   ```python
   # Old
   prepare_phases_for_dara(
       index_path='indexes/merged_index.parquet',
       required_elements=['Li', 'Co', 'O']
   )
   
   # New (MP with stability filtering)
   prepare_phases_for_dara(
       index_path='indexes/mp_index.parquet',
       required_elements=['Li', 'Co', 'O'],
       include_theoretical=True,
       max_e_above_hull=0.1
   )
   ```

#### Breaking Changes
- None (backward compatible)

#### Deprecated
- `filter_icsd.py` - use `database_interface.py` instead
- `filter_cod.py` - use `database_interface.py` instead

---

## Development

### Contributors
- Kedar Group Research Team
- GitHub Copilot (AI Assistant)

### Testing
Run the full test suite:
```bash
pytest scripts/test_pytest_suite.py -v
```

### Building Documentation
```bash
cd docs
make html
```

---

**Last Updated**: October 29, 2025  
**Latest Version**: 3.0.0
