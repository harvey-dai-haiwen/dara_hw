---
title: "Local Database Search Tutorial"
---

# Local Database Search Tutorial

Quick guide to using the local database phase search feature.

## Step-by-Step Workflow

### 0. Username
Enter your username for tracking purposes - helps identify whose pattern is being analyzed.

### 1. Upload XRD Pattern
Supported file formats:
- **.xy** - Two-column ASCII (2θ, intensity)
- **.txt** - Text files with diffraction data
- **.xye** - Three-column format (2θ, intensity, error)
- **.xrdml** - PANalytical/Malvern XML format
- **.raw** - Rigaku/Bruker raw data format

### 2. Select Database
Choose from:
- **MP** - Materials Project
- **ICSD** - Inorganic Crystal Structure Database
- **COD** - Crystallography Open Database

### 3. Specify Elements

**Required Elements** (most important):
- Enter elements that **must** be in the sample
- Example: `Ge Te` finds all structures containing Ge or Te
- Automatically searches unary (Ge, Te), binary (GeTe), and ternary combinations
- **Stays within the specified elemental space** - won't find GeO2 or TeO2 if only "Ge Te" specified

**Exclude Elements** (optional):
- Usually leave blank
- Only use if you need to exclude specific elements

### 4. Other Parameters
Leave wavelength, instrument profile, and other settings at defaults unless you have specific requirements.

### 5. Submit
Click "Submit Search Task" - your job will be added to the queue.

---

## Interpreting Results

### Task Status
After submission, view your task in the queue:
- **Task Label**: Original filename
- **Status**: Current processing state
- **Runtime**: Total computation time
- **Timestamps**: Submission, start, and completion times

### Phase Identification
Once complete, click your task to see:

**Best Fit (Rwp)**: Lower values = better fit quality

**Identified Phases**:
- Representative phases for each composition
- Phase groups (related structures)
- Highlighted phases (major contributors)

**Phase Details**:
- Chemical formula with subscripts
- Database structure ID (COD/ICSD/MP)
- Relative abundance in the sample

### Visualization
Interactive refinement plots show:
- Experimental data (your XRD pattern)
- Calculated fit (from identified phases)
- Difference curve

**Plot Controls**:
- Zoom/pan with mouse
- Hover for detailed values
- Switch between solutions
- Right-click to download images

### Multiple Solutions
Results typically include:
- **Best Solution**: Lowest Rwp value
- **Alternative Solutions**: Other plausible phase combinations
- Easy comparison between different interpretations

---

## Tips

✅ **Typically only specify required elements** - exclude elements rarely needed

✅ **Database selection** - Try COD first (largest, free), then ICSD (curated), then MP (computed)

✅ **Element syntax** - Space-separated: `Y Mo O` or `Ge Te`

✅ **Check multiple solutions** - The best Rwp isn't always the only answer

---

[← Back to Search](/search)
