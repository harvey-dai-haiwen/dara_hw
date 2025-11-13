# Dara Local Server

Extended version of the Dara web server with support for local COD/ICSD/MP database selection.

## What's New

This is a **parallel copy** of the original Dara web server (`src/dara/server`) with the following enhancements:

### ✨ New Features

1. **Local Database Support**
   - COD: Crystallography Open Database (via `indexes/cod_index_filled.parquet`)
   - ICSD: Inorganic Crystal Structure Database (via `indexes/icsd_index_filled.parquet`)
   - MP: Materials Project (via `indexes/mp_index.parquet`)
   - NONE: Use only custom uploaded CIFs

2. **Subset-Based Chemical System Filtering**
   - Same behavior as the streamlined notebook
   - Includes all subsystems (unary, binary, ternary, etc.) in the chemical system
   - Excludes phases with other elements

3. **Materials Project Options**
   - `experimental_only`: Filter to experimental structures only
   - `max_e_above_hull`: Energy threshold for theoretical structures (eV/atom)

4. **New API Endpoint**
   - `POST /api/search`: Direct phase search with database selection
   - Mirrors notebook Part 1-2 functionality

### 🔒 Original Code Untouched

- The original `src/dara/server` remains completely unchanged
- The original server still runs on port **8898**
- This local server runs on port **8899**
- Both can run side-by-side without conflicts

---

## Quick Start

### Prerequisites

1. **Python Environment**
   - Ensure you have activated your environment with Dara installed:
     ```powershell
     conda activate Pymatgen_hw
     # or
     uv sync
     ```

2. **Database Indices**
   - Ensure you have the database indices in the `indexes/` folder:
     - `cod_index_filled.parquet`
     - `icsd_index_filled.parquet` (optional)
     - `mp_index.parquet` (optional)

3. **UI Build** (Optional - only if modifying UI)
   - The UI is already copied from the original
   - If you need to rebuild:
     ```powershell
     cd src\dara_local\server\ui
     yarn install
     yarn build
     ```

### Launch the Server

From the repository root:

```powershell
python launch_local_server.py
```

The server will start on **http://localhost:8899**

---

## API Usage

### New Endpoint: POST /api/search

This endpoint mirrors your streamlined notebook's Part 1-2 behavior.

**Request:**

```bash
POST http://localhost:8899/api/search
Content-Type: multipart/form-data

Fields:
  - pattern_file: file (required) - XRD pattern (.xy, .xrdml, .raw, .txt)
  - required_elements: string (required) - JSON list, e.g., '["Y", "Mo", "O"]'
  - user: string (required) - Username for tracking
  - database: string (default: "COD") - One of: "COD", "ICSD", "MP", "NONE"
  - exclude_elements: string (default: "[]") - JSON list of elements to exclude
  - instrument_profile: string (default: "Aeris-fds-Pixcel1d-Medipix3")
  - wavelength: string (default: "Cu") - "Cu", "Co", "Mo", or wavelength in Å
  - mp_experimental_only: bool (default: false) - MP only: experimental structures
  - mp_max_e_above_hull: float (default: 0.1) - MP only: energy above hull (eV/atom)
  - max_phases: int (default: 500) - Maximum phases to search
  - additional_phases: file[] (optional) - Custom CIF files
```

**Example with cURL:**

```powershell
curl -X POST http://localhost:8899/api/search `
  -F "pattern_file=@path\to\pattern.xy" `
  -F "required_elements=[\"Y\",\"Mo\",\"O\"]" `
  -F "user=researcher" `
  -F "database=COD" `
  -F "max_phases=500"
```

**Example with Python:**

```python
import requests
from pathlib import Path

url = "http://localhost:8899/api/search"

# Prepare data
files = {
    'pattern_file': open('path/to/pattern.xy', 'rb')
}

data = {
    'required_elements': '["Y", "Mo", "O"]',
    'exclude_elements': '[]',
    'user': 'researcher',
    'database': 'COD',  # or 'ICSD', 'MP', 'NONE'
    'instrument_profile': 'Aeris-fds-Pixcel1d-Medipix3',
    'wavelength': 'Cu',
    'max_phases': 500,
    # For MP database:
    # 'mp_experimental_only': False,
    # 'mp_max_e_above_hull': 0.1,
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

**Response:**

```json
{
  "message": "search_completed",
  "status": "COMPLETED",
  "database": "COD",
  "num_phases_searched": 245,
  "num_solutions": 3,
  "best_rwp": 12.34,
  "note": "Direct search result - not queued as background job"
}
```

### Original Endpoint: POST /api/submit

The original endpoint still works unchanged for reaction-network-based workflows:

```bash
POST http://localhost:8899/api/submit
```

---

## Architecture

### File Structure

```
src/dara_local/
├── server/
│   ├── __init__.py
│   ├── app.py                    # FastAPI app (modified: port 8899)
│   ├── api_router.py             # Original endpoints (import paths updated)
│   ├── api_router_extension.py  # NEW: /api/search endpoint
│   ├── setting.py                # Settings (modified: port 8899, DB path)
│   ├── worker.py                 # Background worker (import paths updated)
│   ├── utils.py                  # Utilities (import paths updated)
│   └── ui/                       # Gatsby React UI (API URL → 8899)
│       ├── src/
│       │   └── pages/
│       │       ├── index.js      # Submission form
│       │       ├── results.js    # Results list
│       │       └── task.js       # Task detail
│       └── public/               # Built static files
```

### Key Changes from Original

1. **Import paths**: `dara.server.*` → `dara_local.server.*` (for internal references)
2. **Port**: 8898 → 8899
3. **Database path**: `~/.dara-server/montydb` → `~/.dara-local-server/montydb`
4. **New endpoint**: `api_router_extension.py` adds `/api/search`
5. **UI API URL**: Points to `localhost:8899` in development

---

## Workflow Comparison

### Streamlined Notebook (Part 1-2)

```python
# Define elements and database
required_elements = ['Y', 'Mo', 'O']
DATABASE = "COD"

# Load phases from index
database_cifs = prepare_phases_for_dara(
    index_path=cod_index_path,
    required_elements=required_elements,
    max_phases=500
)

# Run search
search_results = search_phases(
    pattern_path=pattern_path,
    phases=database_cifs,
    wavelength="Cu",
    instrument_profile="Aeris-fds-Pixcel1d-Medipix3"
)
```

### This Web Server (POST /api/search)

```bash
curl -X POST http://localhost:8899/api/search \
  -F "pattern_file=@pattern.xy" \
  -F "required_elements=[\"Y\",\"Mo\",\"O\"]" \
  -F "database=COD" \
  -F "user=researcher"
```

**Both use the same logic:**
- `prepare_phases_for_dara` for database filtering
- `search_phases` for pattern matching
- Subset-based chemical system filtering

---

## Limitations and Future Work

### Current Limitations

1. **Direct Search Only**
   - The `/api/search` endpoint runs searches directly (blocking)
   - For long-running searches, this may timeout
   - **Future**: Queue searches as background jobs like `/api/submit`

2. **No Reaction Network**
   - The `/api/search` endpoint focuses on database selection
   - Reaction-network features still use the original `/api/submit`

3. **UI Not Updated**
   - The UI still uses the original form (no database selector yet)
   - Use the API endpoint directly or via scripts
   - **Future**: Add database selector and element picker to UI

4. **Custom CIF Handling**
   - Custom CIFs are saved to temp directories
   - Not persistent across searches
   - **Future**: Allow server-side CIF library management

### Planned Enhancements

- [ ] Add database selector to UI form
- [ ] Add element selector with validation
- [ ] Queue `/api/search` jobs for background execution
- [ ] Add result caching and job history
- [ ] Support for server-side custom CIF library
- [ ] Diagnostic endpoint for pattern preview

---

## Troubleshooting

### Port Already in Use

If port 8899 is occupied:

1. Stop other services on port 8899
2. Or modify `src/dara_local/server/setting.py`:
   ```python
   port: int = Field(
       default=8900,  # Change to your desired port
       ...
   )
   ```

### Database Index Not Found

Error: `COD index not found at indexes/cod_index_filled.parquet`

**Solution:**
- Ensure database indices exist in the `indexes/` folder
- Run the indexing scripts if needed:
  ```powershell
  python scripts/index_cod_parallel.py
  python scripts/index_icsd.py
  python scripts/index_mp.py
  ```

### Import Errors

Error: `Import "dara_adapter" could not be resolved`

**Solution:**
- The script adds `scripts/` to `sys.path` automatically
- Ensure `scripts/dara_adapter.py` exists
- Ensure you're running from the repository root

### UV Sync Issues

If dependencies are missing:

```powershell
uv sync
```

---

## Testing

### Quick Test with cURL

```powershell
# Test server is running
curl http://localhost:8899/api/tasks

# Test search endpoint (replace with your pattern file)
curl -X POST http://localhost:8899/api/search `
  -F "pattern_file=@notebooks\tutorial_data\GeO2-ZnO_700C_60min.xrdml" `
  -F "required_elements=[\"Ge\",\"Zn\",\"O\"]" `
  -F "user=test" `
  -F "database=COD"
```

### Test with Python

```python
import requests

# Test server health
response = requests.get("http://localhost:8899/api/tasks")
print("Server status:", response.status_code)

# Test search
files = {'pattern_file': open('notebooks/tutorial_data/GeO2-ZnO_700C_60min.xrdml', 'rb')}
data = {
    'required_elements': '["Ge", "Zn", "O"]',
    'user': 'test',
    'database': 'COD'
}
response = requests.post("http://localhost:8899/api/search", files=files, data=data)
print(response.json())
```

---

## License

Same as the original Dara project. See `LICENSE` file.

---

## Summary

This parallel server gives you:
- ✅ Local COD/ICSD/MP database access via web API
- ✅ Notebook Part 1-2 functionality in web form
- ✅ Zero impact on original codebase
- ✅ Side-by-side operation with original server
- ✅ Subset-based chemical system filtering
- ✅ Custom CIF uploads

**Use cases:**
- Run phase searches with your local databases without modifying notebook
- Batch processing via API
- Integration with external tools
- Team collaboration with shared database indices

**Next steps:**
1. Launch the server: `python launch_local_server.py`
2. Test with cURL or Python scripts
3. Optional: Extend the UI to add database selector form fields
