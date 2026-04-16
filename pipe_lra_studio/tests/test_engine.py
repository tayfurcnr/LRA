import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.core.engine import BendingEngine
import numpy as np

def test_lra_90_degree_bend():
    """3 nokta -> 2 vektör -> 2 segment"""
    points = [
        [0, 0, 0],
        [100, 0, 0],
        [100, 100, 0]
    ]
    results = BendingEngine.calculate_lra(points)
    
    assert len(results) == 2, f"Beklenen 2 segment, gelen {len(results)}"
    assert np.isclose(results[0]['L'], 100.0), f"L={results[0]['L']}"
    assert np.isclose(results[0]['A'], 90.0), f"A={results[0]['A']}"
    assert np.isclose(results[1]['L'], 100.0), f"L={results[1]['L']}"
    assert np.isclose(results[1]['A'], 0.0)
    print("✅ 90 Derece Büküm Testi Geçti!")
    for i, r in enumerate(results):
        print(f"   Segment {i+1}: L={r['L']:.2f}, R={r['R']:.2f}, A={r['A']:.2f}")

def test_lra_3d_rotation():
    """4 nokta -> 3 vektör -> 3 segment. 2. büküm rotasyon içermeli."""
    points = [
        [0, 0, 0],
        [100, 0, 0],
        [100, 100, 0],
        [100, 100, 100]
    ]
    results = BendingEngine.calculate_lra(points)
    
    assert len(results) == 3, f"Beklenen 3 segment, gelen {len(results)}"
    # İlk büküm rotasyonu her zaman 0'dır (referans düzlem)
    assert np.isclose(results[1]['R'], 0.0)
    # İkinci büküm (index 2) rotasyon içermeli (düzlem değişimi var)
    assert not np.isclose(results[2]['R'], 0.0), f"Rotasyon 0 olmamalı, gelen: {results[2]['R']}"
    print("✅ 3B Rotasyon Testi Geçti!")
    for i, r in enumerate(results):
        print(f"   Segment {i+1}: L={r['L']:.2f}, R={r['R']:.2f}, A={r['A']:.2f}")

def test_straight_line():
    """Düz hat testi – büküm yok"""
    points = [
        [0, 0, 0],
        [100, 0, 0],
        [200, 0, 0]
    ]
    results = BendingEngine.calculate_lra(points)
    assert len(results) == 2
    assert np.isclose(results[0]['A'], 0.0), "Doğrusal noktada açı 0 olmalı"
    print("✅ Düz Hat Testi Geçti!")

if __name__ == "__main__":
    test_lra_90_degree_bend()
    print()
    test_lra_3d_rotation()
    print()
    test_straight_line()
