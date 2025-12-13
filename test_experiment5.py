#!/usr/bin/env python
"""
Test script for Experiment 5: POI Popularity Alignment
"""

import pandas as pd
from planner.evaluation import evaluate_poi_popularity_alignment

def test_popularity_alignment():
    """Test POI popularity alignment metrics."""
    
    print("=== Testing POI Popularity Alignment Metrics ===\n")
    
    # Test Case 1: Perfect alignment
    print("Test 1: Perfect alignment (identical rankings)")
    planned = [(1, 100), (2, 80), (3, 60), (4, 40), (5, 20)]
    real = [(1, 100), (2, 80), (3, 60), (4, 40), (5, 20)]
    
    metrics = evaluate_poi_popularity_alignment(planned, real, k=3)
    print(f"  Top-K Overlap: {metrics.top_k_overlap:.4f} (expected: 1.0)")
    print(f"  Spearman Correlation: {metrics.spearman_correlation:.4f} (expected: 1.0)")
    print(f"  Coverage@K: {metrics.coverage_at_k:.4f} (expected: 1.0)")
    assert abs(metrics.top_k_overlap - 1.0) < 0.01, "Top-K overlap should be 1.0"
    assert abs(metrics.spearman_correlation - 1.0) < 0.01, "Spearman should be 1.0"
    assert abs(metrics.coverage_at_k - 1.0) < 0.01, "Coverage@K should be 1.0"
    print("  ✓ Passed\n")
    
    # Test Case 2: Reversed rankings
    print("Test 2: Reversed rankings")
    planned = [(1, 100), (2, 80), (3, 60), (4, 40), (5, 20)]
    real = [(5, 100), (4, 80), (3, 60), (2, 40), (1, 20)]
    
    metrics = evaluate_poi_popularity_alignment(planned, real, k=3)
    print(f"  Top-K Overlap: {metrics.top_k_overlap:.4f} (expected: ~0.33)")
    print(f"  Spearman Correlation: {metrics.spearman_correlation:.4f} (expected: -1.0)")
    print(f"  Coverage@K: {metrics.coverage_at_k:.4f} (expected: 1.0)")
    assert abs(metrics.spearman_correlation - (-1.0)) < 0.01, "Spearman should be -1.0"
    print("  ✓ Passed\n")
    
    # Test Case 3: Partial overlap
    print("Test 3: Partial overlap")
    planned = [(1, 100), (2, 80), (3, 60), (4, 40), (5, 20)]
    real = [(1, 100), (6, 90), (2, 85), (7, 70), (3, 65)]
    
    metrics = evaluate_poi_popularity_alignment(planned, real, k=3)
    print(f"  Top-K Overlap: {metrics.top_k_overlap:.4f}")
    print(f"  Spearman Correlation: {metrics.spearman_correlation:.4f}")
    print(f"  Coverage@K: {metrics.coverage_at_k:.4f}")
    # Top-3 planned: {1, 2, 3}, Top-3 real: {1, 6, 2} -> overlap = 2/3 = 0.667
    assert abs(metrics.top_k_overlap - 0.667) < 0.01, f"Top-K overlap should be ~0.667, got {metrics.top_k_overlap}"
    # Coverage: top-3 real {1, 6, 2} in all planned {1,2,3,4,5} -> 2/3 = 0.667
    assert abs(metrics.coverage_at_k - 0.667) < 0.01, f"Coverage@K should be ~0.667, got {metrics.coverage_at_k}"
    print("  ✓ Passed\n")
    
    # Test Case 4: No overlap
    print("Test 4: No overlap in top-K")
    planned = [(1, 100), (2, 80), (3, 60)]
    real = [(4, 100), (5, 80), (6, 60)]
    
    metrics = evaluate_poi_popularity_alignment(planned, real, k=3)
    print(f"  Top-K Overlap: {metrics.top_k_overlap:.4f} (expected: 0.0)")
    print(f"  Spearman Correlation: {metrics.spearman_correlation:.4f} (expected: 0.0)")
    print(f"  Coverage@K: {metrics.coverage_at_k:.4f} (expected: 0.0)")
    assert abs(metrics.top_k_overlap) < 0.01, "Top-K overlap should be 0.0"
    assert abs(metrics.coverage_at_k) < 0.01, "Coverage@K should be 0.0"
    print("  ✓ Passed\n")
    
    print("=== All tests passed! ===")


if __name__ == "__main__":
    test_popularity_alignment()
