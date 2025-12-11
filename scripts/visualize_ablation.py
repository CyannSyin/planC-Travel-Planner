"""
Standalone script to visualize ablation study results from saved evaluation report.

从保存的评估报告中可视化消融实验结果的独立脚本。
"""

from pathlib import Path
import sys
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from planner.visualization import (
    visualize_ablation_study,
    visualize_ablation_heatmap,
    visualize_ablation_comparison_table
)


def load_ablation_from_csv(csv_path: Path):
    """Load ablation results from evaluation summary CSV."""
    import pandas as pd
    
    df = pd.read_csv(csv_path)
    
    # Check if ablation_results column exists
    if 'ablation_results' not in df.columns:
        raise ValueError("No 'ablation_results' column found in CSV file")
    
    # Parse JSON string if present
    ablation_str = df.iloc[0]['ablation_results']
    if isinstance(ablation_str, str):
        import ast
        ablation_results = ast.literal_eval(ablation_str)
    else:
        ablation_results = ablation_str
    
    return ablation_results


def load_ablation_from_json(json_path: Path):
    """Load ablation results from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'ablation_results' in data:
        return data['ablation_results']
    else:
        # Assume the entire file is ablation results
        return data


def main():
    """Main function to visualize ablation results."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Visualize ablation study results"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="results/evaluation_summary.csv",
        help="Input file path (CSV or JSON)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="Output directory for visualization images"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display plots interactively"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        print("\nUsage examples:")
        print("  python scripts/visualize_ablation.py --input results/evaluation_summary.csv")
        print("  python scripts/visualize_ablation.py --input results/evaluation_summary.json --show")
        return
    
    # Load ablation results
    print(f"Loading ablation results from: {input_path}")
    try:
        if input_path.suffix == '.csv':
            ablation_results = load_ablation_from_csv(input_path)
        elif input_path.suffix == '.json':
            ablation_results = load_ablation_from_json(input_path)
        else:
            raise ValueError(f"Unsupported file format: {input_path.suffix}")
    except Exception as e:
        print(f"Error loading ablation results: {e}")
        return
    
    if not ablation_results:
        print("Error: No ablation results found in input file")
        return
    
    print(f"Found {len(ablation_results)} ablation configurations")
    
    # Generate visualizations
    print("\nGenerating visualizations...")
    
    try:
        # 1. Combined bar charts
        visualize_ablation_study(
            ablation_results=ablation_results,
            output_path=output_dir / "ablation_visualization.pdf",
            show_plot=args.show,
        )
        
        # 2. Heatmap for route length
        visualize_ablation_heatmap(
            ablation_results=ablation_results,
            output_path=output_dir / "ablation_heatmap_length.pdf",
            metric='route_length_km',
            show_plot=args.show,
        )
        
        # 3. Heatmap for time efficiency
        visualize_ablation_heatmap(
            ablation_results=ablation_results,
            output_path=output_dir / "ablation_heatmap_efficiency.pdf",
            metric='time_efficiency',
            show_plot=args.show,
        )
        
        # 4. Comparison table
        visualize_ablation_comparison_table(
            ablation_results=ablation_results,
            output_path=output_dir / "ablation_comparison_table.pdf",
            show_plot=args.show,
        )
        
        print("\n✓ All visualizations generated successfully!")
        print(f"  Output directory: {output_dir}")
        
    except ImportError as e:
        print(f"\nError: Missing required packages. {e}")
        print("Please install required packages:")
        print("  pip install matplotlib seaborn")
    except Exception as e:
        print(f"\nError generating visualizations: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

