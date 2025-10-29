# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

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
