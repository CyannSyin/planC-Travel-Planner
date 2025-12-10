"""
Visualization utilities for experiment results, especially ablation studies.

实验结果显示与可视化工具，特别针对消融实验。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False

# 设置中文字体支持
# Try to use Chinese fonts if available, fallback to default
try:
    import matplotlib.font_manager as fm
    # Check for common Chinese fonts
    chinese_fonts = ['Arial Unicode MS', 'SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei']
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    found_font = None
    for font in chinese_fonts:
        if font in available_fonts:
            found_font = font
            break
    if found_font:
        matplotlib.rcParams['font.sans-serif'] = [found_font] + matplotlib.rcParams['font.sans-serif']
except Exception:
    pass  # Fallback to default fonts

matplotlib.rcParams['axes.unicode_minus'] = False


def visualize_ablation_study(
    ablation_results: Dict[str, Dict],
    output_path: Optional[Path] = None,
    figsize: tuple = (18, 6),
    dpi: int = 100,
    show_plot: bool = True,
):
    """Visualize ablation study results with multiple chart types.
    
    可视化消融实验结果，包含：
    - 柱状图：对比不同配置下的路线长度和时间效率
    - 热力图：展示配置组合的性能矩阵
    
    Args:
        ablation_results: Dictionary with ablation results, format:
            {
                "pop_1_2opt_1": {
                    "route_length_km": 278.28,
                    "time_efficiency": 0.31
                },
                ...
            }
        output_path: Path to save the figure (default: results/ablation_visualization.png)
        figsize: Figure size (width, height)
        dpi: Resolution for saved figure
        show_plot: Whether to display the plot interactively
    """
    
    if not ablation_results:
        print("Warning: No ablation results provided for visualization.")
        return
    
    # 转换为 DataFrame 便于处理
    data_list = []
    for setting_name, metrics in ablation_results.items():
        # 解析配置名称: pop_1_2opt_1 -> (use_pop=True, use_2opt=True)
        parts = setting_name.split('_')
        use_pop = parts[1] == '1'
        use_2opt = parts[3] == '1'
        
        data_list.append({
            'Setting': setting_name,
            'Use Popularity': 'Yes' if use_pop else 'No',
            'Use 2-opt': 'Yes' if use_2opt else 'No',
            'Route Length (km)': metrics.get('route_length_km', 0.0),
            'Time Efficiency': metrics.get('time_efficiency', 0.0),
            'Clustering Silhouette': metrics.get('clustering_silhouette', 0.0),
            'N Days': metrics.get('n_days', 0),
        })
    
    df = pd.DataFrame(data_list)
    
    # 创建图形：2x2 布局（调整为3列：路线长度、时间效率、聚类质量）
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Ablation Study Results / 消融实验结果', fontsize=16, fontweight='bold')
    
    # 1. 路线长度对比柱状图
    ax1 = axes[0]
    x_pos = range(len(df))
    colors = ['#4CAF50' if df.loc[i, 'Use 2-opt'] == 'Yes' else '#FF9800' 
              for i in range(len(df))]
    
    bars1 = ax1.bar(x_pos, df['Route Length (km)'], color=colors, alpha=0.7, edgecolor='black')
    ax1.set_xlabel('Configuration / 配置', fontsize=11)
    ax1.set_ylabel('Avg Route Length (km) / 平均路线长度 (公里)', fontsize=11)
    ax1.set_title('Route Length Comparison / 路线长度对比', fontsize=12, fontweight='bold')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(df['Setting'], rotation=45, ha='right', fontsize=9)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    
    # 添加数值标签
    for i, (bar, val) in enumerate(zip(bars1, df['Route Length (km)'])):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.2f}',
                ha='center', va='bottom', fontsize=8)
    
    # 添加图例
    from matplotlib.patches import Patch
    legend_elements1 = [
        Patch(facecolor='#4CAF50', alpha=0.7, label='With 2-opt / 使用2-opt'),
        Patch(facecolor='#FF9800', alpha=0.7, label='Without 2-opt / 不使用2-opt')
    ]
    ax1.legend(handles=legend_elements1, loc='upper right', fontsize=8)
    
    # 2. 时间效率对比柱状图
    ax2 = axes[1]
    colors2 = ['#2196F3' if df.loc[i, 'Use Popularity'] == 'Yes' else '#F44336' 
               for i in range(len(df))]
    
    bars2 = ax2.bar(x_pos, df['Time Efficiency'], color=colors2, alpha=0.7, edgecolor='black')
    ax2.set_xlabel('Configuration / 配置', fontsize=11)
    ax2.set_ylabel('Time Efficiency / 时间效率', fontsize=11)
    ax2.set_title('Time Efficiency Comparison / 时间效率对比', fontsize=12, fontweight='bold')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(df['Setting'], rotation=45, ha='right', fontsize=9)
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    if len(df) > 0 and df['Time Efficiency'].max() > 0:
        ax2.set_ylim([0, max(df['Time Efficiency']) * 1.2])
    
    # 添加数值标签
    for i, (bar, val) in enumerate(zip(bars2, df['Time Efficiency'])):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.3f}',
                ha='center', va='bottom', fontsize=8)
    
    # 添加图例
    legend_elements2 = [
        Patch(facecolor='#2196F3', alpha=0.7, label='With Popularity / 使用popularity'),
        Patch(facecolor='#F44336', alpha=0.7, label='Without Popularity / 不使用popularity')
    ]
    ax2.legend(handles=legend_elements2, loc='upper right', fontsize=8)
    
    # 3. 聚类质量对比（新增）
    ax3 = axes[2]
    colors3 = ['#9C27B0' if df.loc[i, 'Use Popularity'] == 'Yes' else '#E91E63' 
               for i in range(len(df))]
    
    bars3 = ax3.bar(x_pos, df['Clustering Silhouette'], color=colors3, alpha=0.7, edgecolor='black')
    ax3.set_xlabel('Configuration / 配置', fontsize=11)
    ax3.set_ylabel('Clustering Silhouette Score / 聚类轮廓系数', fontsize=11)
    ax3.set_title('Clustering Quality / 聚类质量', fontsize=12, fontweight='bold')
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(df['Setting'], rotation=45, ha='right', fontsize=9)
    ax3.grid(axis='y', alpha=0.3, linestyle='--')
    if len(df) > 0 and df['Clustering Silhouette'].max() > 0:
        ax3.set_ylim([0, max(df['Clustering Silhouette']) * 1.2])
    
    # 添加数值标签
    for i, (bar, val) in enumerate(zip(bars3, df['Clustering Silhouette'])):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.3f}',
                ha='center', va='bottom', fontsize=8)
    
    # 添加图例
    legend_elements3 = [
        Patch(facecolor='#9C27B0', alpha=0.7, label='With Popularity / 使用popularity'),
        Patch(facecolor='#E91E63', alpha=0.7, label='Without Popularity / 不使用popularity')
    ]
    ax3.legend(handles=legend_elements3, loc='upper right', fontsize=8)
    
    plt.tight_layout()
    
    # 保存图片
    if output_path is None:
        output_path = Path("results/ablation_visualization.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    print(f"✓ Ablation visualization saved to: {output_path}")
    
    if show_plot:
        plt.show()
    else:
        plt.close()
    
    return fig


def visualize_ablation_heatmap(
    ablation_results: Dict[str, Dict],
    output_path: Optional[Path] = None,
    figsize: tuple = (10, 6),
    dpi: int = 100,
    show_plot: bool = True,
    metric: str = 'route_length_km',
):
    """Visualize ablation results as a heatmap showing the effect of different configurations.
    
    使用热力图展示消融实验结果，显示不同配置组合的性能。
    
    Args:
        ablation_results: Dictionary with ablation results
        output_path: Path to save the figure
        figsize: Figure size
        dpi: Resolution for saved figure
        show_plot: Whether to display the plot interactively
        metric: Metric to visualize ('route_length_km' or 'time_efficiency')
    """
    
    if not ablation_results:
        print("Warning: No ablation results provided for visualization.")
        return
    
    # 构建矩阵数据
    data = {}
    for setting_name, metrics in ablation_results.items():
        parts = setting_name.split('_')
        use_pop = parts[1] == '1'
        use_2opt = parts[3] == '1'
        
        key = (use_pop, use_2opt)
        if metric == 'route_length_km':
            data[key] = metrics.get('route_length_km', 0.0)
        elif metric == 'time_efficiency':
            data[key] = metrics.get('time_efficiency', 0.0)
        else:
            raise ValueError(f"Unknown metric: {metric}")
    
    # 创建矩阵
    matrix = pd.DataFrame([
        [data.get((False, False), 0), data.get((False, True), 0)],
        [data.get((True, False), 0), data.get((True, True), 0)]
    ], 
    index=['No Popularity', 'With Popularity'],
    columns=['No 2-opt', 'With 2-opt'])
    
    # 创建热力图
    if not HAS_SEABORN:
        raise ImportError(
            "seaborn is required for heatmap visualization. "
            "Install it with: pip install seaborn"
        )
    
    fig, ax = plt.subplots(figsize=figsize)
    
    sns.heatmap(
        matrix, 
        annot=True, 
        fmt='.2f', 
        cmap='YlOrRd' if metric == 'route_length_km' else 'YlGnBu',
        cbar_kws={'label': 'Route Length (km)' if metric == 'route_length_km' else 'Time Efficiency'},
        ax=ax,
        linewidths=1,
        linecolor='black',
        square=False
    )
    
    metric_title = 'Route Length (km)' if metric == 'route_length_km' else 'Time Efficiency'
    title = f'Ablation Study Heatmap - {metric_title} / 消融实验热力图 - {metric_title}'
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('2-opt Optimization / 2-opt优化', fontsize=12)
    ax.set_ylabel('Popularity Feature /  popularity特征', fontsize=12)
    
    plt.tight_layout()
    
    # 保存图片
    if output_path is None:
        metric_suffix = 'length' if metric == 'route_length_km' else 'efficiency'
        output_path = Path(f"results/ablation_heatmap_{metric_suffix}.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    print(f"✓ Ablation heatmap saved to: {output_path}")
    
    if show_plot:
        plt.show()
    else:
        plt.close()
    
    return fig


def visualize_ablation_comparison_table(
    ablation_results: Dict[str, Dict],
    output_path: Optional[Path] = None,
    figsize: tuple = (12, 4),
    dpi: int = 100,
    show_plot: bool = True,
):
    """Create a comparison table visualization for ablation results.
    
    创建消融实验结果的对比表格可视化。
    
    Args:
        ablation_results: Dictionary with ablation results
        output_path: Path to save the figure
        figsize: Figure size
        dpi: Resolution for saved figure
        show_plot: Whether to display the plot interactively
    """
    
    if not ablation_results:
        print("Warning: No ablation results provided for visualization.")
        return
    
    # 准备数据
    data_list = []
    for setting_name, metrics in ablation_results.items():
        parts = setting_name.split('_')
        use_pop = parts[1] == '1'
        use_2opt = parts[3] == '1'
        
        data_list.append({
            'Popularity': '✓' if use_pop else '✗',
            '2-opt': '✓' if use_2opt else '✗',
            'Days': str(metrics.get('n_days', 0)),
            'Silhouette': f"{metrics.get('clustering_silhouette', 0.0):.3f}",
            'Route Length\n(km)': f"{metrics.get('route_length_km', 0.0):.2f}",
            'Time Efficiency': f"{metrics.get('time_efficiency', 0.0):.3f}",
        })
    
    df = pd.DataFrame(data_list)
    
    # 创建表格图
    fig, ax = plt.subplots(figsize=figsize)
    ax.axis('tight')
    ax.axis('off')
    
    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc='center',
        loc='center',
        bbox=[0, 0, 1, 1]
    )
    
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2)
    
    # 设置表头样式
    for i in range(len(df.columns)):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # 设置单元格样式
    for i in range(1, len(df) + 1):
        for j in range(len(df.columns)):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#f0f0f0')
            else:
                table[(i, j)].set_facecolor('white')
    
    plt.title('Ablation Study Comparison Table / 消融实验对比表', 
              fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    # 保存图片
    if output_path is None:
        output_path = Path("results/ablation_comparison_table.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    print(f"✓ Ablation comparison table saved to: {output_path}")
    
    if show_plot:
        plt.show()
    else:
        plt.close()
    
    return fig

