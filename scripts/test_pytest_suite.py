"""
Pytest 单元测试套件
测试 database_interface 和 dara_adapter 的核心功能
"""

import pytest
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database_interface import StructureDatabaseIndex
from dara_adapter import prepare_phases_for_dara, get_index_stats


# ============================================================================
# Fixtures
# ============================================================================

# Get workspace root (parent of scripts/)
WORKSPACE_ROOT = Path(__file__).parent.parent

@pytest.fixture(scope="module")
def db_merged():
    """Load merged index (ICSD+COD)"""
    return StructureDatabaseIndex(WORKSPACE_ROOT / 'indexes/merged_index.parquet')


@pytest.fixture(scope="module")
def db_mp():
    """Load MP index"""
    return StructureDatabaseIndex(WORKSPACE_ROOT / 'indexes/mp_index.parquet')


@pytest.fixture(scope="module")
def db_icsd():
    """Load ICSD index"""
    return StructureDatabaseIndex(WORKSPACE_ROOT / 'indexes/icsd_index_filled.parquet')


# ============================================================================
# Test StructureDatabaseIndex - Basic Queries
# ============================================================================

class TestBasicQueries:
    """Test basic query functionality"""
    
    def test_load_merged_index(self, db_merged):
        """Test loading merged index"""
        assert len(db_merged.df) > 700000
        assert 'source' in db_merged.df.columns
        assert set(db_merged.df['source'].unique()) == {'ICSD', 'COD'}
    
    def test_load_mp_index(self, db_mp):
        """Test loading MP index"""
        assert len(db_mp.df) == 169385
        assert 'experimental_status' in db_mp.df.columns
        assert 'energy_above_hull' in db_mp.df.columns
    
    def test_filter_by_elements(self, db_merged):
        """Test element filtering"""
        fe_o = db_merged.filter_by_elements(['Fe', 'O'])
        assert len(fe_o) > 0
        # All results should contain Fe and O
        for elements in fe_o['elements'].head(10):
            if isinstance(elements, list):
                assert 'Fe' in elements
                assert 'O' in elements
    
    def test_filter_by_formula(self, db_merged):
        """Test formula filtering"""
        tio2 = db_merged.filter_by_formula('TiO2')
        assert len(tio2) > 0
    
    def test_filter_by_density(self, db_merged):
        """Test density filtering"""
        dense = db_merged.filter_by_density(min_val=5.0, max_val=10.0)
        assert len(dense) > 0
        # Check density range
        assert dense['density'].min() >= 5.0
        assert dense['density'].max() <= 10.0
    
    def test_filter_by_spacegroup(self, db_merged):
        """Test spacegroup filtering"""
        cubic = db_merged.filter_by_spacegroup(['Fm-3m'])
        assert len(cubic) > 0


# ============================================================================
# Test MP-specific Features
# ============================================================================

class TestMPFeatures:
    """Test MP-specific query features"""
    
    def test_experimental_status_experimental(self, db_mp):
        """Test experimental status filtering - experimental"""
        exp = db_mp.filter_by_experimental_status('experimental')
        assert len(exp) > 0
        # All should be experimental
        assert all(exp['experimental_status'] == 'experimental')
    
    def test_experimental_status_theoretical(self, db_mp):
        """Test experimental status filtering - theoretical"""
        theo = db_mp.filter_by_experimental_status('theoretical')
        assert len(theo) > 0
        # All should be theoretical
        assert all(theo['experimental_status'] == 'theoretical')
    
    def test_experimental_status_all(self, db_mp):
        """Test experimental status filtering - all"""
        all_data = db_mp.filter_by_experimental_status('all')
        assert len(all_data) == len(db_mp.df)
    
    def test_experimental_theoretical_sum(self, db_mp):
        """Test that experimental + theoretical = total"""
        exp = db_mp.filter_by_experimental_status('experimental')
        theo = db_mp.filter_by_experimental_status('theoretical')
        total = len(exp) + len(theo)
        assert total == len(db_mp.df)
    
    def test_stability_filter(self, db_mp):
        """Test stability filtering"""
        stable = db_mp.filter_by_stability(max_e_above_hull=0.0)
        # Filter MP data only
        stable_mp = stable[stable['source'] == 'MP']
        assert len(stable_mp) > 0
        # Check energy range
        assert stable_mp['energy_above_hull'].max() <= 0.0
    
    def test_stability_thresholds(self, db_mp):
        """Test different stability thresholds"""
        stable_0 = db_mp.filter_by_stability(max_e_above_hull=0.0)
        stable_01 = db_mp.filter_by_stability(max_e_above_hull=0.1)
        
        # More permissive threshold should have more results
        assert len(stable_01) >= len(stable_0)


# ============================================================================
# Test ICSD/COD Behavior
# ============================================================================

class TestICSDCODBehavior:
    """Test ICSD/COD specific behavior"""
    
    def test_icsd_all_experimental(self, db_icsd):
        """Test that ICSD data is all experimental"""
        exp = db_icsd.filter_by_experimental_status('experimental')
        assert len(exp) == len(db_icsd.df)
    
    def test_icsd_no_theoretical(self, db_icsd):
        """Test that ICSD has no theoretical structures"""
        theo = db_icsd.filter_by_experimental_status('theoretical')
        assert len(theo) == 0
    
    def test_merged_no_theoretical(self, db_merged):
        """Test that merged index (ICSD+COD) has no theoretical"""
        theo = db_merged.filter_by_experimental_status('theoretical')
        assert len(theo) == 0


# ============================================================================
# Test DARA Adapter
# ============================================================================

class TestDARAAdapter:
    """Test DARA adapter functionality"""
    
    def test_prepare_phases_basic(self):
        """Test basic phase preparation"""
        phases = prepare_phases_for_dara(
            index_path=WORKSPACE_ROOT / 'indexes/mp_index.parquet',
            required_elements=['Li', 'O'],
            experimental_only=True,
            max_phases=50
        )
        assert len(phases) <= 50
        assert len(phases) > 0
        # All should be valid paths
        assert all(isinstance(p, str) for p in phases)
    
    def test_prepare_phases_experimental_only(self):
        """Test experimental_only parameter"""
        exp_phases = prepare_phases_for_dara(
            index_path=WORKSPACE_ROOT / 'indexes/mp_index.parquet',
            required_elements=['Fe', 'O'],
            experimental_only=True,
            max_phases=100
        )
        assert len(exp_phases) > 0
    
    def test_prepare_phases_include_theoretical(self):
        """Test include_theoretical parameter"""
        mixed_phases = prepare_phases_for_dara(
            index_path=WORKSPACE_ROOT / 'indexes/mp_index.parquet',
            required_elements=['Li', 'Co', 'O'],
            include_theoretical=True,
            max_e_above_hull=0.1,
            max_phases=100
        )
        # Should have some results
        assert len(mixed_phases) > 0
    
    def test_prepare_phases_stability_filter(self):
        """Test stability filtering in dara_adapter"""
        stable = prepare_phases_for_dara(
            index_path=WORKSPACE_ROOT / 'indexes/mp_index.parquet',
            required_elements=['Li', 'O'],
            include_theoretical=True,
            max_e_above_hull=0.01,
            max_phases=100
        )
        
        less_stable = prepare_phases_for_dara(
            index_path=WORKSPACE_ROOT / 'indexes/mp_index.parquet',
            required_elements=['Li', 'O'],
            include_theoretical=True,
            max_e_above_hull=0.1,
            max_phases=100
        )
        
        # More permissive should have >= results
        assert len(less_stable) >= len(stable)
    
    def test_prepare_phases_empty_result(self):
        """Test handling of empty results"""
        empty = prepare_phases_for_dara(
            index_path=WORKSPACE_ROOT / 'indexes/mp_index.parquet',
            required_elements=['Unobtanium'],
            max_phases=100
        )
        assert len(empty) == 0
    
    def test_get_index_stats(self):
        """Test index statistics"""
        stats = get_index_stats(WORKSPACE_ROOT / 'indexes/mp_index.parquet')
        assert 'total_records' in stats
        assert 'sources' in stats
        assert stats['total_records'] == 169385


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_query(self, db_merged):
        """Test empty query result"""
        empty = db_merged.filter_by_formula('Unobtanium123')
        assert len(empty) == 0
    
    def test_negative_density(self, db_merged):
        """Test negative density filter"""
        negative = db_merged.filter_by_density(min_val=-1.0, max_val=0.0)
        assert len(negative) == 0
    
    def test_very_high_density(self, db_merged):
        """Test very high density filter"""
        high = db_merged.filter_by_density(min_val=20.0, max_val=30.0)
        # Might have results (heavy elements), but should not error
        assert len(high) >= 0
    
    def test_max_phases_limit(self):
        """Test max_phases parameter"""
        phases = prepare_phases_for_dara(
            index_path=WORKSPACE_ROOT / 'indexes/merged_index.parquet',
            required_elements=['O'],
            max_phases=50
        )
        assert len(phases) == 50


# ============================================================================
# Test Data Integrity
# ============================================================================

class TestDataIntegrity:
    """Test data integrity and consistency"""
    
    def test_mp_experimental_status_values(self, db_mp):
        """Test MP experimental_status only has valid values"""
        valid_values = {'experimental', 'theoretical'}
        actual_values = set(db_mp.df['experimental_status'].unique())
        assert actual_values.issubset(valid_values)
    
    def test_mp_energy_above_hull_numeric(self, db_mp):
        """Test energy_above_hull is numeric"""
        energy_col = db_mp.df['energy_above_hull']
        # All non-null values should be numeric
        numeric_values = energy_col.dropna()
        assert all(isinstance(x, (int, float)) for x in numeric_values.head(100))
    
    def test_spacegroup_coverage(self, db_mp):
        """Test MP has 100% spacegroup coverage"""
        coverage = db_mp.df['spacegroup'].notna().sum() / len(db_mp.df)
        assert coverage == 1.0
    
    def test_path_coverage(self, db_mp):
        """Test MP has 100% path coverage"""
        coverage = db_mp.df['path'].notna().sum() / len(db_mp.df)
        assert coverage == 1.0


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])

