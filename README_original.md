![DARA logo](docs/_static/logo-with-text.svg)

# DARA: Data-driven automated Rietveld analysis for phase search and refinement

Automated phase search with BGMN.

## ✨ What's New

**Version 3.0** (October 2025) - Multi-Database Integration
- 🗃️ **Materials Project (MP) Support**: 169,385 structures with experimental/theoretical classification
- 🔬 **Experimental/Theoretical Filtering**: Distinguish between experimental and DFT-computed structures
- ⚡ **Thermodynamic Stability**: Filter phases by `energy_above_hull` for battery/catalyst research
- 🎯 **Unified Query Interface**: Single API for ICSD, COD, and MP databases
- 📊 **900k+ Total Structures**: ICSD (229k) + COD (502k) + MP (169k)

See [CHANGELOG.md](CHANGELOG.md) for detailed changes.

---

## 📚 Database Support

DARA now integrates three major crystal structure databases:

| Database | Entries | Type | Spacegroup Coverage |
|----------|---------|------|---------------------|
| **ICSD** | 229,487 | Experimental | 97.2% |
| **COD** | 501,975 | Experimental | 98.5% |
| **Materials Project (MP)** | 169,385 | Mixed (35% Exp + 65% Theory) | 100% |
| **Total** | 900,847 | - | 98.6% |

**Quick Example:**
```python
from scripts.dara_adapter import prepare_phases_for_dara

# Get stable Li-Mn-O phases from Materials Project
cif_paths = prepare_phases_for_dara(
    index_path='indexes/mp_index.parquet',
    required_elements=['Li', 'Mn', 'O'],
    include_theoretical=True,
    max_e_above_hull=0.1  # Only stable/metastable phases
)

# Use in DARA PhaseSearchMaker
from dara import PhaseSearchMaker
maker = PhaseSearchMaker(
    required_elements=['Li', 'Mn', 'O'],
    additional_phases=cif_paths
)
```

See [scripts/README.md](scripts/README.md) for complete database documentation.

---

## Installation
```bash
pip install dara-xrd
```

For more details about installation, please refer to [installation guide](https://idocx.github.io/dara/install.html).

## Web Server
Dara ships with a browser-based web server for an out-of-box experience of Dara. To launch the webserver, run
```bash
dara server
```

Then you can open http://localhost:8898 to see an application that can submit, manage, and view jobs.
