param(
  [string]$IcsdCsvPath = "D:\\Data\\ICSD\\[Kedar_Group_ONLY]_ICSD2024_summary_2024.2_v5.3.0.csv",
  [string]$CodArchivePath = "D:\\Data\\COD\\cod-cifs-mysql.txz",
  [string]$MpPicklePath = "D:\\Data\\MP\\df_MP_20250211.pkl",
  [string]$RepoRoot = (Resolve-Path "$PSScriptRoot\..\").Path
)

Write-Host "=== Dara 3.0 Database Setup (ICSD, COD, MP) ===" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot" -ForegroundColor DarkGray

# Ensure directories
$codDir = Join-Path $RepoRoot 'cod_cifs'
$icsdDir = Join-Path $RepoRoot 'icsd_cifs'
$mpDir = Join-Path $RepoRoot 'mp_cifs'
$idxDir = Join-Path $RepoRoot 'indexes'

$null = New-Item -ItemType Directory -Force -Path $codDir, $icsdDir, $mpDir, $idxDir

function Require-File($path, $hint) {
  if (-not (Test-Path $path)) {
    Write-Host "Missing: $path" -ForegroundColor Red
    Write-Host "Hint: $hint" -ForegroundColor Yellow
    exit 1
  }
}

# 1) ICSD
Write-Host "\n[1/4] ICSD indexing" -ForegroundColor Green
Require-File $IcsdCsvPath "Provide ICSD CSV export with inline CIFs"

Write-Host "-> Building ICSD index (parquet)"
pushd $RepoRoot
python scripts/index_icsd.py `
  --csv "$IcsdCsvPath" `
  --out "$idxDir/icsd_index.parquet" || exit 1

Write-Host "-> Extracting ICSD CIFs and filling spacegroups"
python scripts/extract_icsd_cifs.py `
  --csv "$IcsdCsvPath" `
  --index "$idxDir/icsd_index.parquet" `
  --cif-dir "$icsdDir" `
  --out "$idxDir/icsd_index_filled.parquet" || exit 1
popd

# 2) COD
Write-Host "\n[2/4] COD indexing" -ForegroundColor Green
Require-File $CodArchivePath "Download cod-cifs-mysql.txz from COD and set CodArchivePath"

Write-Host "-> Extracting COD archive (this may take hours)"
pushd $RepoRoot
try {
  tar -xJf "$CodArchivePath" -C "$codDir"
} catch {
  Write-Host "tar extraction failed. Ensure tar is available or extract manually using 7-Zip into $codDir" -ForegroundColor Yellow
}

Write-Host "-> Building COD index (parallel)"
python scripts/index_cod_parallel.py `
  --cif-dir "$codDir" `
  --out "$idxDir/cod_index.parquet" `
  --workers 16 || exit 1

Write-Host "-> Filling COD spacegroups (sequential for stability)"
python scripts/fill_spacegroup_cod.py `
  --index "$idxDir/cod_index.parquet" `
  --cif-dir "$codDir" `
  --out "$idxDir/cod_index_filled.parquet" `
  --workers 1 || exit 1
popd

# 3) MP
Write-Host "\n[3/4] MP indexing" -ForegroundColor Green
Require-File $MpPicklePath "Provide Materials Project pickle file with Structures"

Write-Host "-> Building MP index and exporting CIFs"
pushd $RepoRoot
python scripts/index_mp.py `
  --input "$MpPicklePath" `
  --output "$idxDir/mp_index.parquet" `
  --cif-dir "$mpDir" || exit 1
popd

# 4) Merge
Write-Host "\n[4/4] Merge and validate" -ForegroundColor Green
pushd $RepoRoot
python scripts/merge_indices.py `
  --parquets "$idxDir/icsd_index_filled.parquet" "$idxDir/cod_index_filled.parquet" "$idxDir/mp_index.parquet" `
  --out-parquet "$idxDir/merged_index.parquet" `
  --out-json "$idxDir/merged_index.json.gz" `
  --out-sqlite "$idxDir/merged_index.sqlite" || exit 1

python scripts/verify_indices.py "$idxDir/icsd_index_filled.parquet"
python scripts/verify_indices.py "$idxDir/cod_index_filled.parquet"
python scripts/verify_mp_index.py "$idxDir/mp_index.parquet"
python scripts/verify_merged.py "$idxDir/merged_index.parquet"
popd

Write-Host "\n✅ Done. Indexes are in: $idxDir" -ForegroundColor Cyan
Write-Host "Next: run 'jupyter lab' and open notebooks/streamlined_phase_analysis.ipynb" -ForegroundColor DarkGray
