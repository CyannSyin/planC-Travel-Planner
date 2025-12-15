"""
Visualization utilities for experiment results, especially ablation studies.

"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
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
        output_path: Path to save the figure (default: results/ablation_visualization.pdf)
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
    fig.suptitle('Ablation Study Results', fontsize=16, fontweight='bold')
    
    # 1. 路线长度对比柱状图
    ax1 = axes[0]
    x_pos = range(len(df))
    colors = ['#4CAF50' if df.loc[i, 'Use 2-opt'] == 'Yes' else '#FF9800' 
              for i in range(len(df))]
    
    bars1 = ax1.bar(x_pos, df['Route Length (km)'], color=colors, alpha=0.7, edgecolor='black')
    ax1.set_xlabel('Configuration', fontsize=11)
    ax1.set_ylabel('Avg Route Length (km)', fontsize=11)
    ax1.set_title('Route Length Comparison', fontsize=12, fontweight='bold')
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
        Patch(facecolor='#4CAF50', alpha=0.7, label='With 2-opt'),
        Patch(facecolor='#FF9800', alpha=0.7, label='Without 2-opt')
    ]
    ax1.legend(handles=legend_elements1, loc='upper right', fontsize=8)
    
    # 2. 时间效率对比柱状图
    ax2 = axes[1]
    colors2 = ['#2196F3' if df.loc[i, 'Use Popularity'] == 'Yes' else '#F44336' 
               for i in range(len(df))]
    
    bars2 = ax2.bar(x_pos, df['Time Efficiency'], color=colors2, alpha=0.7, edgecolor='black')
    ax2.set_xlabel('Configuration', fontsize=11)
    ax2.set_ylabel('Time Efficiency', fontsize=11)
    ax2.set_title('Time Efficiency Comparison ', fontsize=12, fontweight='bold')
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
        Patch(facecolor='#2196F3', alpha=0.7, label='With Popularity'),
        Patch(facecolor='#F44336', alpha=0.7, label='Without Popularity')
    ]
    ax2.legend(handles=legend_elements2, loc='upper right', fontsize=8)
    
    # 3. 聚类质量对比（新增）
    ax3 = axes[2]
    colors3 = ['#9C27B0' if df.loc[i, 'Use Popularity'] == 'Yes' else '#E91E63' 
               for i in range(len(df))]
    
    bars3 = ax3.bar(x_pos, df['Clustering Silhouette'], color=colors3, alpha=0.7, edgecolor='black')
    ax3.set_xlabel('Configuration', fontsize=11)
    ax3.set_ylabel('Clustering Silhouette Score', fontsize=11)
    ax3.set_title('Clustering Quality', fontsize=12, fontweight='bold')
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
        Patch(facecolor='#9C27B0', alpha=0.7, label='With Popularity'),
        Patch(facecolor='#E91E63', alpha=0.7, label='Without Popularity')
    ]
    ax3.legend(handles=legend_elements3, loc='upper right', fontsize=8)
    
    plt.tight_layout()
    
    # 保存图片
    if output_path is None:
        output_path = Path("results/ablation_visualization.pdf")
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
    title = f'Ablation Study Heatmap - {metric_title} - {metric_title}'
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('2-opt Optimization', fontsize=12)
    ax.set_ylabel('Popularity Feature', fontsize=12)
    
    plt.tight_layout()
    
    # 保存图片
    if output_path is None:
        metric_suffix = 'length' if metric == 'route_length_km' else 'efficiency'
        output_path = Path(f"results/ablation_heatmap_{metric_suffix}.pdf")
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
    
    plt.title('Ablation Study Comparison Table', 
              fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    # 保存图片
    if output_path is None:
        output_path = Path("results/ablation_comparison_table.pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    print(f"✓ Ablation comparison table saved to: {output_path}")
    
    if show_plot:
        plt.show()
    else:
        plt.close()
    
    return fig


def visualize_experiment_1_clustering_map(
    pois: pd.DataFrame,
    cluster_result,
    output_path: Optional[Path] = None,
    figsize: tuple = (14, 10),
    dpi: int = 100,
    show_plot: bool = True,
):
    """Visualize Experiment 1 clustering results on a map.
    
    在地图上可视化实验1的聚类结果，展示POI如何被分配到不同的天数。
    
    Args:
        pois: DataFrame with POIs containing 'lat' and 'lon' columns
        cluster_result: ClusteringResult object with labels
        output_path: Path to save the figure (default: results/experiment1_clustering_map.pdf)
        figsize: Figure size (width, height)
        dpi: Resolution for saved figure
        show_plot: Whether to display the plot interactively
    """
    if pois is None or len(pois) == 0:
        print("Warning: No POIs provided for map visualization.")
        return
    
    if 'lat' not in pois.columns or 'lon' not in pois.columns:
        print("Warning: POIs DataFrame missing 'lat' or 'lon' columns.")
        return
    
    labels = cluster_result.labels
    n_clusters = cluster_result.n_clusters
    
    # 过滤掉噪声点（DBSCAN的-1标签）
    valid_mask = labels >= 0
    pois_valid = pois[valid_mask].copy()
    labels_valid = labels[valid_mask]
    
    if len(pois_valid) == 0:
        print("Warning: No valid POIs after filtering noise points.")
        return
    
    # 创建图形
    fig, ax = plt.subplots(figsize=figsize)
    
    # 为每个cluster分配不同颜色
    colors = plt.cm.tab20(np.linspace(0, 1, max(n_clusters, 20)))
    
    # 绘制每个cluster的POI
    for cluster_id in range(n_clusters):
        cluster_mask = labels_valid == cluster_id
        cluster_pois = pois_valid[cluster_mask]
        
        if len(cluster_pois) == 0:
            continue
        
        ax.scatter(
            cluster_pois['lon'], 
            cluster_pois['lat'],
            c=[colors[cluster_id % len(colors)]],
            label=f'Day {cluster_id} ({len(cluster_pois)} POIs)',
            s=100,
            alpha=0.6,
            edgecolors='black',
            linewidths=1
        )
        
        # 添加cluster中心
        center_lon = cluster_pois['lon'].mean()
        center_lat = cluster_pois['lat'].mean()
        ax.scatter(
            center_lon, center_lat,
            c='red',
            marker='*',
            s=500,
            edgecolors='black',
            linewidths=2,
            zorder=5,
            label=f'Day {cluster_id} Center' if cluster_id == 0 else ""
        )
    
    # 绘制噪声点（如果有）
    noise_mask = ~valid_mask
    if noise_mask.sum() > 0:
        noise_pois = pois[noise_mask]
        ax.scatter(
            noise_pois['lon'],
            noise_pois['lat'],
            c='gray',
            marker='x',
            s=50,
            alpha=0.3,
            label=f'Noise ({noise_mask.sum()} POIs)'
        )
    
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.set_title(f'Experiment 1: POI Clustering Map\n{n_clusters} Days / {len(pois_valid)} POIs', 
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=9, ncol=2)
    
    plt.tight_layout()
    
    if output_path is None:
        output_path = Path("results/experiment1_clustering_map.pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    print(f"✓ Experiment 1 clustering map saved to: {output_path}")
    
    if show_plot:
        plt.show()
    else:
        plt.close()
    
    return fig


def visualize_experiment_1_clustering(
    cluster_results: Dict,
    output_path: Optional[Path] = None,
    figsize: tuple = (16, 10),
    dpi: int = 100,
    show_plot: bool = True,
):
    """Visualize Experiment 1 (POI Clustering) results.
    
    可视化实验1（POI聚类）结果，包含：
    - 不同聚类方法的指标对比
    - 聚类数量对比
    - 聚类质量指标柱状图
    
    Args:
        cluster_results: Dictionary with clustering results, format:
            {
                "kmeans": ClusteringResult(...),
                "hac": ClusteringResult(...),
                ...
            }
        output_path: Path to save the figure (default: results/experiment1_clustering.pdf)
        figsize: Figure size (width, height)
        dpi: Resolution for saved figure
        show_plot: Whether to display the plot interactively
    """
    
    if not cluster_results:
        print("Warning: No clustering results provided for visualization.")
        return
    
    # 准备数据
    methods = []
    n_clusters_list = []
    silhouette_list = []
    davies_bouldin_list = []
    calinski_harabasz_list = []
    sci_list = []
    
    for method, result in cluster_results.items():
        methods.append(method.upper())
        n_clusters_list.append(result.n_clusters)
        silhouette_list.append(result.silhouette if result.silhouette is not None else 0.0)
        davies_bouldin_list.append(result.davies_bouldin if result.davies_bouldin is not None else 0.0)
        calinski_harabasz_list.append(result.calinski_harabasz if result.calinski_harabasz is not None else 0.0)
        sci_list.append(result.sci if result.sci is not None else 0.0)
    
    # 创建图形：2x3 布局
    fig, axes = plt.subplots(2, 3, figsize=figsize)
    fig.suptitle('Experiment 1: POI Clustering Results', 
                 fontsize=16, fontweight='bold')
    
    x_pos = np.arange(len(methods))
    colors = plt.cm.Set3(np.linspace(0, 1, len(methods)))
    
    # 1. 聚类数量对比
    ax1 = axes[0, 0]
    bars1 = ax1.bar(x_pos, n_clusters_list, color=colors, alpha=0.7, edgecolor='black')
    ax1.set_xlabel('Clustering Method', fontsize=11)
    ax1.set_ylabel('Number of Clusters', fontsize=11)
    ax1.set_title('Number of Clusters', fontsize=12, fontweight='bold')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(methods, rotation=0, fontsize=10)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    
    # 添加数值标签
    for bar, val in zip(bars1, n_clusters_list):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(val)}',
                ha='center', va='bottom', fontsize=9)
    
    # 2. Silhouette Score（越高越好，范围[-1, 1]）
    ax2 = axes[0, 1]
    bars2 = ax2.bar(x_pos, silhouette_list, color=colors, alpha=0.7, edgecolor='black')
    ax2.set_xlabel('Clustering Method', fontsize=11)
    ax2.set_ylabel('Silhouette Score', fontsize=11)
    ax2.set_title('Silhouette Score (Higher is Better)', fontsize=12, fontweight='bold')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(methods, rotation=0, fontsize=10)
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    ax2.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)
    
    # 添加数值标签
    for bar, val in zip(bars2, silhouette_list):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.3f}',
                ha='center', va='bottom' if val >= 0 else 'top', fontsize=9)
    
    # 3. Davies-Bouldin Index（越低越好）
    ax3 = axes[0, 2]
    bars3 = ax3.bar(x_pos, davies_bouldin_list, color=colors, alpha=0.7, edgecolor='black')
    ax3.set_xlabel('Clustering Method', fontsize=11)
    ax3.set_ylabel('Davies-Bouldin Index', fontsize=11)
    ax3.set_title('Davies-Bouldin Index (Lower is Better)', fontsize=12, fontweight='bold')
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(methods, rotation=0, fontsize=10)
    ax3.grid(axis='y', alpha=0.3, linestyle='--')
    
    # 添加数值标签
    for bar, val in zip(bars3, davies_bouldin_list):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.3f}',
                ha='center', va='bottom', fontsize=9)
    
    # 4. Calinski-Harabasz Index（越高越好）
    ax4 = axes[1, 0]
    bars4 = ax4.bar(x_pos, calinski_harabasz_list, color=colors, alpha=0.7, edgecolor='black')
    ax4.set_xlabel('Clustering Method', fontsize=11)
    ax4.set_ylabel('Calinski-Harabasz Index', fontsize=11)
    ax4.set_title('Calinski-Harabasz Index (Higher is Better)', fontsize=12, fontweight='bold')
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(methods, rotation=0, fontsize=10)
    ax4.grid(axis='y', alpha=0.3, linestyle='--')
    
    # 添加数值标签（如果值太大，显示科学计数法）
    for bar, val in zip(bars4, calinski_harabasz_list):
        height = bar.get_height()
        if val > 1000:
            label = f'{val:.2e}'
        else:
            label = f'{val:.1f}'
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                label,
                ha='center', va='bottom', fontsize=9)
    
    # 5. SCI Index（越高越好）
    ax5 = axes[1, 1]
    bars5 = ax5.bar(x_pos, sci_list, color=colors, alpha=0.7, edgecolor='black')
    ax5.set_xlabel('Clustering Method', fontsize=11)
    ax5.set_ylabel('SCI Index', fontsize=11)
    ax5.set_title('SCI Index (Higher is Better)', fontsize=12, fontweight='bold')
    ax5.set_xticks(x_pos)
    ax5.set_xticklabels(methods, rotation=0, fontsize=10)
    ax5.grid(axis='y', alpha=0.3, linestyle='--')
    
    # 添加数值标签
    for bar, val in zip(bars5, sci_list):
        height = bar.get_height()
        ax5.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.3f}',
                ha='center', va='bottom', fontsize=9)
    
    # 6. 综合对比（归一化后的综合评分）
    ax6 = axes[1, 2]
    # 归一化各个指标（除了n_clusters，因为它不能直接比较）
    # Silhouette: 已经在[-1, 1]范围内，+1后缩放到[0, 1]
    norm_silhouette = [(s + 1) / 2.0 for s in silhouette_list]
    # Davies-Bouldin: 反转并归一化（越低越好）
    max_db = max(davies_bouldin_list) if max(davies_bouldin_list) > 0 else 1.0
    norm_db = [1.0 - (db / max_db) for db in davies_bouldin_list]
    # Calinski-Harabasz: 归一化
    max_ch = max(calinski_harabasz_list) if max(calinski_harabasz_list) > 0 else 1.0
    norm_ch = [ch / max_ch for ch in calinski_harabasz_list]
    # SCI: 归一化
    max_sci = max(sci_list) if max(sci_list) > 0 else 1.0
    norm_sci = [sci / max_sci for sci in sci_list]
    
    # 综合评分（平均）
    composite_scores = [
        (ns + ndb + nch + nsci) / 4.0 
        for ns, ndb, nch, nsci in zip(norm_silhouette, norm_db, norm_ch, norm_sci)
    ]
    
    bars6 = ax6.bar(x_pos, composite_scores, color=colors, alpha=0.7, edgecolor='black')
    ax6.set_xlabel('Clustering Method', fontsize=11)
    ax6.set_ylabel('Normalized Composite Score', fontsize=11)
    ax6.set_title('Normalized Composite Score', fontsize=12, fontweight='bold')
    ax6.set_xticks(x_pos)
    ax6.set_xticklabels(methods, rotation=0, fontsize=10)
    ax6.grid(axis='y', alpha=0.3, linestyle='--')
    ax6.set_ylim([0, 1.1])
    
    # 添加数值标签
    for bar, val in zip(bars6, composite_scores):
        height = bar.get_height()
        ax6.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.3f}',
                ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    
    # 保存图片
    if output_path is None:
        output_path = Path("results/experiment1_clustering.pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    print(f"✓ Experiment 1 clustering visualization saved to: {output_path}")
    
    if show_plot:
        plt.show()
    else:
        plt.close()
    
    return fig


def visualize_experiment_2_routes_map(
    day_pois: Dict[int, pd.DataFrame],
    routes: Dict[int, List[int]],
    output_path: Optional[Path] = None,
    figsize: tuple = (14, 10),
    dpi: int = 100,
    show_plot: bool = True,
):
    """Visualize Experiment 2 route optimization results on a map.
    
    在地图上可视化实验2的路线优化结果，展示每天的优化路线。
    
    Args:
        day_pois: Dictionary mapping day to DataFrame with POIs for that day
        routes: Dictionary mapping day to list of POI indices (route order)
        output_path: Path to save the figure (default: results/experiment2_routes_map.pdf)
        figsize: Figure size (width, height)
        dpi: Resolution for saved figure
        show_plot: Whether to display the plot interactively
    """
    if not day_pois or not routes:
        print("Warning: No day_pois or routes provided for map visualization.")
        return
    
    days = sorted(day_pois.keys())
    n_days = len(days)
    
    # 确定子图布局
    if n_days <= 2:
        n_cols = n_days
        n_rows = 1
    elif n_days <= 4:
        n_cols = 2
        n_rows = 2
    elif n_days <= 6:
        n_cols = 3
        n_rows = 2
    else:
        n_cols = 3
        n_rows = (n_days + 2) // 3
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    fig.suptitle('Experiment 2: Daily Route Optimization Map', 
                 fontsize=16, fontweight='bold')
    
    # 确保axes是数组
    if n_days == 1:
        axes = [axes]
    else:
        axes = axes.flatten() if hasattr(axes, 'flatten') else [axes]
    
    colors = plt.cm.tab10(np.linspace(0, 1, n_days))
    
    for idx, day in enumerate(days):
        ax = axes[idx] if idx < len(axes) else axes[-1]
        
        if day not in day_pois or day not in routes:
            ax.text(0.5, 0.5, f'Day {day}: No data', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')
            continue
        
        day_df = day_pois[day].reset_index(drop=True)
        route = routes[day]
        
        if len(route) == 0:
            ax.text(0.5, 0.5, f'Day {day}: No route', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')
            continue
        
        # 绘制所有POI点
        ax.scatter(
            day_df['lon'],
            day_df['lat'],
            c='lightgray',
            s=50,
            alpha=0.5,
            edgecolors='black',
            linewidths=0.5,
            label='POIs'
        )
        
        # 绘制路线
        route_coords = []
        for poi_idx in route:
            if poi_idx < len(day_df):
                poi = day_df.iloc[poi_idx]
                route_coords.append((poi['lon'], poi['lat']))
        
        if len(route_coords) > 1:
            route_lons, route_lats = zip(*route_coords)
            # 绘制路线连接
            ax.plot(
                route_lons, route_lats,
                color=colors[idx],
                linewidth=2,
                alpha=0.7,
                linestyle='-',
                marker='o',
                markersize=8,
                markerfacecolor=colors[idx],
                markeredgecolor='black',
                markeredgewidth=1,
                label=f'Route ({len(route_coords)} POIs)'
            )
            
            # 标记起点
            ax.scatter(
                route_lons[0], route_lats[0],
                c='green',
                marker='s',
                s=200,
                edgecolors='black',
                linewidths=2,
                zorder=5,
                label='Start'
            )
            
            # 标记终点
            if len(route_coords) > 1:
                ax.scatter(
                    route_lons[-1], route_lats[-1],
                    c='red',
                    marker='*',
                    s=300,
                    edgecolors='black',
                    linewidths=2,
                    zorder=5,
                    label='End'
                )
            
            # 添加路线方向箭头（在路线的中间部分）
            for i in range(len(route_coords) - 1):
                mid_idx = len(route_coords) // 2
                if i == mid_idx and len(route_coords) > 2:
                    dx = route_lons[i+1] - route_lons[i]
                    dy = route_lats[i+1] - route_lats[i]
                    # 归一化箭头长度
                    scale = 0.0001  # 调整箭头大小
                    ax.arrow(
                        route_lons[i], route_lats[i],
                        dx * scale, dy * scale,
                        head_width=0.0002, head_length=0.0002,
                        fc=colors[idx], ec='black',
                        linewidth=1.5,
                        zorder=4
                    )
        
        # 添加POI序号标签（只显示前几个，避免拥挤）
        max_labels = min(5, len(route))
        for i, poi_idx in enumerate(route[:max_labels]):
            if poi_idx < len(day_df):
                poi = day_df.iloc[poi_idx]
                ax.annotate(
                    str(i+1),
                    (poi['lon'], poi['lat']),
                    xytext=(5, 5),
                    textcoords='offset points',
                    fontsize=8,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7)
                )
        
        ax.set_xlabel('Longitude', fontsize=10)
        ax.set_ylabel('Latitude', fontsize=10)
        ax.set_title(f'Day {day} Route', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=8)
    
    # 隐藏多余的子图
    for idx in range(n_days, len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    
    if output_path is None:
        output_path = Path("results/experiment2_routes_map.pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    print(f"✓ Experiment 2 routes map saved to: {output_path}")
    
    if show_plot:
        plt.show()
    else:
        plt.close()
    
    return fig


def visualize_experiment_2_routes(
    route_metrics: Dict[int, Dict],
    day_pois: Optional[Dict[int, pd.DataFrame]] = None,
    output_path: Optional[Path] = None,
    figsize: tuple = (16, 10),
    dpi: int = 100,
    show_plot: bool = True,
):
    """Visualize Experiment 2 (Daily Route Optimization) results.
    
    可视化实验2（每日路线优化）结果，包含：
    - 每天的路线长度
    - 每天的时间效率
    - 每天的POI数量
    - 回退比等指标
    
    Args:
        route_metrics: Dictionary with route metrics for each day, format:
            {
                0: {"length_km": 50.2, "time_efficiency": 0.85, "backtracking_ratio": 1.2, ...},
                1: {...},
                ...
            }
        day_pois: Optional dictionary with POIs for each day (used for POI count)
        output_path: Path to save the figure (default: results/experiment2_routes.pdf)
        figsize: Figure size (width, height)
        dpi: Resolution for saved figure
        show_plot: Whether to display the plot interactively
    """
    
    if not route_metrics:
        print("Warning: No route metrics provided for visualization.")
        return
    
    # 准备数据
    days = sorted(route_metrics.keys())
    route_lengths = [route_metrics[day].get('length_km', 0.0) for day in days]
    time_efficiencies = [route_metrics[day].get('time_efficiency', 0.0) for day in days]
    backtracking_ratios = [route_metrics[day].get('backtracking_ratio', 0.0) for day in days]
    
    # POI数量（如果有day_pois数据）
    if day_pois:
        poi_counts = [len(day_pois.get(day, pd.DataFrame())) for day in days]
    else:
        poi_counts = None
    
    # 创建图形：2x3 布局
    fig, axes = plt.subplots(2, 3, figsize=figsize)
    fig.suptitle('Experiment 2: Daily Route Optimization Results', 
                 fontsize=16, fontweight='bold')
    
    x_pos = np.arange(len(days))
    colors = plt.cm.viridis(np.linspace(0, 1, len(days)))
    
    # 1. 路线长度对比
    ax1 = axes[0, 0]
    bars1 = ax1.bar(x_pos, route_lengths, color=colors, alpha=0.7, edgecolor='black')
    ax1.set_xlabel('Day', fontsize=11)
    ax1.set_ylabel('Route Length (km)', fontsize=11)
    ax1.set_title('Route Length per Day', fontsize=12, fontweight='bold')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels([f'Day {d}' for d in days], rotation=0, fontsize=10)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    
    # 添加数值标签
    for bar, val in zip(bars1, route_lengths):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.2f}',
                ha='center', va='bottom', fontsize=9)
    
    # 2. 时间效率对比
    ax2 = axes[0, 1]
    bars2 = ax2.bar(x_pos, time_efficiencies, color=colors, alpha=0.7, edgecolor='black')
    ax2.set_xlabel('Day', fontsize=11)
    ax2.set_ylabel('Time Efficiency', fontsize=11)
    ax2.set_title('Time Efficiency per Day', fontsize=12, fontweight='bold')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels([f'Day {d}' for d in days], rotation=0, fontsize=10)
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    
    # 添加数值标签
    for bar, val in zip(bars2, time_efficiencies):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.3f}',
                ha='center', va='bottom', fontsize=9)
    
    # 3. 回退比对比
    ax3 = axes[0, 2]
    bars3 = ax3.bar(x_pos, backtracking_ratios, color=colors, alpha=0.7, edgecolor='black')
    ax3.set_xlabel('Day', fontsize=11)
    ax3.set_ylabel('Backtracking Ratio', fontsize=11)
    ax3.set_title('Backtracking Ratio per Day', fontsize=12, fontweight='bold')
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels([f'Day {d}' for d in days], rotation=0, fontsize=10)
    ax3.grid(axis='y', alpha=0.3, linestyle='--')
    ax3.axhline(y=1.0, color='red', linestyle='--', linewidth=1, label='Baseline (1.0)')
    ax3.legend(fontsize=8)
    
    # 添加数值标签
    for bar, val in zip(bars3, backtracking_ratios):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.3f}',
                ha='center', va='bottom', fontsize=9)
    
    # 4. POI数量对比（如果有数据）
    ax4 = axes[1, 0]
    if poi_counts:
        bars4 = ax4.bar(x_pos, poi_counts, color=colors, alpha=0.7, edgecolor='black')
        ax4.set_xlabel('Day', fontsize=11)
        ax4.set_ylabel('Number of POIs', fontsize=11)
        ax4.set_title('POIs per Day', fontsize=12, fontweight='bold')
        ax4.set_xticks(x_pos)
        ax4.set_xticklabels([f'Day {d}' for d in days], rotation=0, fontsize=10)
        ax4.grid(axis='y', alpha=0.3, linestyle='--')
        
        # 添加数值标签
        for bar, val in zip(bars4, poi_counts):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(val)}',
                    ha='center', va='bottom', fontsize=9)
    else:
        ax4.text(0.5, 0.5, 'POI count data not available', 
                ha='center', va='center', transform=ax4.transAxes, fontsize=12)
        ax4.axis('off')
    
    # 5. 路线长度 vs 时间效率散点图
    ax5 = axes[1, 1]
    scatter = ax5.scatter(route_lengths, time_efficiencies, 
                         c=range(len(days)), cmap='viridis', 
                         s=100, alpha=0.6, edgecolors='black')
    ax5.set_xlabel('Route Length (km)', fontsize=11)
    ax5.set_ylabel('Time Efficiency', fontsize=11)
    ax5.set_title('Route Length vs Time Efficiency', 
                 fontsize=12, fontweight='bold')
    ax5.grid(alpha=0.3, linestyle='--')
    
    # 添加标签
    for i, day in enumerate(days):
        ax5.annotate(f'Day {day}', 
                    (route_lengths[i], time_efficiencies[i]),
                    xytext=(5, 5), textcoords='offset points', fontsize=8)
    
    # 添加颜色条
    cbar = plt.colorbar(scatter, ax=ax5)
    cbar.set_label('Day', fontsize=9)
    
    # 6. 汇总统计
    ax6 = axes[1, 2]
    ax6.axis('off')
    
    total_length = sum(route_lengths)
    avg_length = total_length / len(days) if days else 0.0
    avg_efficiency = sum(time_efficiencies) / len(time_efficiencies) if time_efficiencies else 0.0
    avg_backtracking = sum(backtracking_ratios) / len(backtracking_ratios) if backtracking_ratios else 0.0
    total_pois = sum(poi_counts) if poi_counts else 0
    
    summary_text = f"""
Summary Statistics
{'=' * 30}
Total Days: {len(days)}
Total Route Length: {total_length:.2f} km
Average Route Length: {avg_length:.2f} km/day
Average Time Efficiency: {avg_efficiency:.3f}
Average Backtracking Ratio: {avg_backtracking:.3f}
"""
    if poi_counts:
        summary_text += f"Total POIs: {total_pois}\n"
        summary_text += f"Average POIs per Day: {total_pois / len(days):.1f}\n"
    
    ax6.text(0.1, 0.5, summary_text, 
            transform=ax6.transAxes, fontsize=11,
            verticalalignment='center', family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    # 保存图片
    if output_path is None:
        output_path = Path("results/experiment2_routes.pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    print(f"✓ Experiment 2 routes visualization saved to: {output_path}")
    
    if show_plot:
        plt.show()
    else:
        plt.close()
    
    return fig


def visualize_experiment_5_popularity_alignment(
    popularity_metrics: Dict,
    planned_popularity: List[tuple],
    real_popularity: List[tuple],
    output_path: Optional[Path] = None,
    figsize: tuple = (18, 10),
    dpi: int = 100,
    show_plot: bool = True,
    top_n: int = 20,
):
    """Visualize Experiment 5 (POI Popularity Alignment) results.
    
    可视化实验5（POI热度对齐）结果，包含：
    - Top-K POI重叠率、Spearman相关性、Coverage@K指标
    - 规划路线与真实轨迹的POI热度排名对比
    - 热门POI的访问频率对比
    
    Args:
        popularity_metrics: Dictionary with popularity alignment metrics
        planned_popularity: List of (poi_id, visit_count) tuples from planned routes
        real_popularity: List of (poi_id, visit_count) tuples from real trajectories
        output_path: Path to save the figure
        figsize: Figure size (width, height)
        dpi: Resolution for saved figure
        show_plot: Whether to display the plot interactively
        top_n: Number of top POIs to display in ranking comparison
    """
    
    if not popularity_metrics:
        print("Warning: No popularity metrics provided for visualization.")
        return
    
    # 创建图形：2x3 布局
    fig, axes = plt.subplots(2, 3, figsize=figsize)
    fig.suptitle('Experiment 5: POI Popularity Alignment Results', 
                 fontsize=16, fontweight='bold')
    
    # 1. 指标柱状图
    ax1 = axes[0, 0]
    metrics_names = ['Top-K\nOverlap', 'Spearman\nCorrelation', 'Coverage@K']
    metrics_values = [
        popularity_metrics.get('top_k_overlap', 0.0),
        popularity_metrics.get('spearman_correlation', 0.0),
        popularity_metrics.get('coverage_at_k', 0.0)
    ]
    colors_metrics = ['#4CAF50', '#2196F3', '#FF9800']
    
    bars1 = ax1.bar(range(len(metrics_names)), metrics_values, 
                    color=colors_metrics, alpha=0.7, edgecolor='black')
    ax1.set_xlabel('Metrics', fontsize=11)
    ax1.set_ylabel('Score', fontsize=11)
    ax1.set_title(f'Popularity Alignment Metrics (K={popularity_metrics.get("k", 10)})', 
                  fontsize=12, fontweight='bold')
    ax1.set_xticks(range(len(metrics_names)))
    ax1.set_xticklabels(metrics_names, fontsize=10)
    ax1.set_ylim([-0.1, 1.1])
    ax1.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    
    # 添加数值标签
    for bar, val in zip(bars1, metrics_values):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.3f}',
                ha='center', va='bottom' if val >= 0 else 'top', fontsize=10)
    
    # 2. Top-N POI排名对比（规划 vs 真实）
    ax2 = axes[0, 1]
    
    # 获取Top-N POI
    top_n_planned = planned_popularity[:min(top_n, len(planned_popularity))]
    top_n_real = real_popularity[:min(top_n, len(real_popularity))]
    
    # 创建POI ID到排名的映射
    planned_ranks = {poi_id: rank for rank, (poi_id, _) in enumerate(top_n_planned, 1)}
    real_ranks = {poi_id: rank for rank, (poi_id, _) in enumerate(top_n_real, 1)}
    
    # 找到共同的POI
    common_pois = set(planned_ranks.keys()) & set(real_ranks.keys())
    
    if common_pois:
        common_poi_list = sorted(list(common_pois), 
                                key=lambda x: planned_ranks[x])
        
        planned_rank_values = [planned_ranks[poi] for poi in common_poi_list]
        real_rank_values = [real_ranks[poi] for poi in common_poi_list]
        
        # 绘制排名对比散点图
        ax2.scatter(planned_rank_values, real_rank_values, 
                   s=100, alpha=0.6, edgecolors='black', c='#9C27B0')
        
        # 添加对角线（完美对齐）
        max_rank = max(max(planned_rank_values), max(real_rank_values))
        ax2.plot([1, max_rank], [1, max_rank], 'r--', linewidth=2, 
                alpha=0.5, label='Perfect Alignment')
        
        ax2.set_xlabel('Planned Route Rank', fontsize=11)
        ax2.set_ylabel('Real Trajectory Rank', fontsize=11)
        ax2.set_title(f'Top-{top_n} POI Rank Comparison\n({len(common_pois)} common POIs)', 
                     fontsize=12, fontweight='bold')
        ax2.grid(alpha=0.3, linestyle='--')
        ax2.legend(fontsize=9)
        
        # 反转Y轴使排名从上到下递增
        ax2.invert_yaxis()
        ax2.invert_xaxis()
    else:
        ax2.text(0.5, 0.5, 'No common POIs in Top-N', 
                ha='center', va='center', transform=ax2.transAxes, fontsize=12)
        ax2.axis('off')
    
    # 3. 访问频率对比（Top-10）
    ax3 = axes[0, 2]
    
    top_10_planned = planned_popularity[:min(10, len(planned_popularity))]
    top_10_real = real_popularity[:min(10, len(real_popularity))]
    
    # 获取所有Top-10 POI的并集
    all_top_pois = set([poi_id for poi_id, _ in top_10_planned] + 
                       [poi_id for poi_id, _ in top_10_real])
    
    # 创建POI ID到访问次数的映射
    planned_counts = {poi_id: count for poi_id, count in top_10_planned}
    real_counts = {poi_id: count for poi_id, count in top_10_real}
    
    # 准备数据
    poi_labels = [f'POI-{poi_id}' for poi_id in sorted(all_top_pois)[:10]]
    planned_values = [planned_counts.get(poi_id, 0) for poi_id in sorted(all_top_pois)[:10]]
    real_values = [real_counts.get(poi_id, 0) for poi_id in sorted(all_top_pois)[:10]]
    
    x_pos = np.arange(len(poi_labels))
    width = 0.35
    
    bars_planned = ax3.bar(x_pos - width/2, planned_values, width, 
                          label='Planned', color='#4CAF50', alpha=0.7, edgecolor='black')
    bars_real = ax3.bar(x_pos + width/2, real_values, width,
                       label='Real', color='#FF5722', alpha=0.7, edgecolor='black')
    
    ax3.set_xlabel('POI ID', fontsize=11)
    ax3.set_ylabel('Visit Count', fontsize=11)
    ax3.set_title('Top-10 POI Visit Frequency Comparison', fontsize=12, fontweight='bold')
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(poi_labels, rotation=45, ha='right', fontsize=9)
    ax3.legend(fontsize=9)
    ax3.grid(axis='y', alpha=0.3, linestyle='--')
    
    # 4. 规划路线POI热度分布
    ax4 = axes[1, 0]
    
    if len(planned_popularity) > 0:
        planned_counts_only = [count for _, count in planned_popularity[:30]]
        ax4.plot(range(1, len(planned_counts_only) + 1), planned_counts_only,
                marker='o', linewidth=2, markersize=6, color='#4CAF50', 
                label='Planned Route')
        ax4.fill_between(range(1, len(planned_counts_only) + 1), 
                        planned_counts_only, alpha=0.3, color='#4CAF50')
        
        ax4.set_xlabel('POI Rank', fontsize=11)
        ax4.set_ylabel('Visit Count', fontsize=11)
        ax4.set_title('Planned Route POI Popularity Distribution', 
                     fontsize=12, fontweight='bold')
        ax4.grid(alpha=0.3, linestyle='--')
        ax4.legend(fontsize=9)
    else:
        ax4.text(0.5, 0.5, 'No planned popularity data', 
                ha='center', va='center', transform=ax4.transAxes, fontsize=12)
        ax4.axis('off')
    
    # 5. 真实轨迹POI热度分布
    ax5 = axes[1, 1]
    
    if len(real_popularity) > 0:
        real_counts_only = [count for _, count in real_popularity[:30]]
        ax5.plot(range(1, len(real_counts_only) + 1), real_counts_only,
                marker='s', linewidth=2, markersize=6, color='#FF5722',
                label='Real Trajectory')
        ax5.fill_between(range(1, len(real_counts_only) + 1), 
                        real_counts_only, alpha=0.3, color='#FF5722')
        
        ax5.set_xlabel('POI Rank', fontsize=11)
        ax5.set_ylabel('Visit Count', fontsize=11)
        ax5.set_title('Real Trajectory POI Popularity Distribution', 
                     fontsize=12, fontweight='bold')
        ax5.grid(alpha=0.3, linestyle='--')
        ax5.legend(fontsize=9)
    else:
        ax5.text(0.5, 0.5, 'No real popularity data', 
                ha='center', va='center', transform=ax5.transAxes, fontsize=12)
        ax5.axis('off')
    
    # 6. 汇总统计
    ax6 = axes[1, 2]
    ax6.axis('off')
    
    k = popularity_metrics.get('k', 10)
    top_k_overlap = popularity_metrics.get('top_k_overlap', 0.0)
    spearman = popularity_metrics.get('spearman_correlation', 0.0)
    coverage = popularity_metrics.get('coverage_at_k', 0.0)
    planned_unique = popularity_metrics.get('planned_unique_pois', 0)
    real_unique = popularity_metrics.get('real_unique_pois', 0)
    
    summary_text = f"""
POI Popularity Alignment
{'=' * 35}
Top-K (K={k}):
  Overlap: {top_k_overlap:.3f}
  Coverage@K: {coverage:.3f}

Rank Correlation:
  Spearman: {spearman:.3f}

POI Statistics:
  Planned Unique POIs: {planned_unique}
  Real Unique POIs: {real_unique}
  Common POIs: {len(common_pois) if common_pois else 0}

Interpretation:
  • Top-K Overlap: {top_k_overlap*100:.1f}% of top-{k}
    POIs match between planned
    and real trajectories
  • Spearman: {'Strong' if abs(spearman) > 0.7 else 'Moderate' if abs(spearman) > 0.4 else 'Weak'} 
    {'positive' if spearman > 0 else 'negative'} correlation
  • Coverage@K: {coverage*100:.1f}% of top-{k}
    real POIs are covered in plan
"""
    
    ax6.text(0.05, 0.5, summary_text, 
            transform=ax6.transAxes, fontsize=10,
            verticalalignment='center', family='monospace',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))
    
    plt.tight_layout()
    
    # 保存图片
    if output_path is None:
        output_path = Path("results/experiment5_popularity.pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    print(f"✓ Experiment 5 popularity alignment visualization saved to: {output_path}")
    
    if show_plot:
        plt.show()
    else:
        plt.close()
    
    return fig
