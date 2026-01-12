"""
Beer Game Comparison Visualizer - V4
Genera gráficos a partir de los datos comparativos del script compare_results_v4.py
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
import sys

def load_and_compare_data(json_file):
    """Carga y procesa los datos para visualización"""
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Extract weekly results from structure
    weekly_results = {}
    for week_data in data.get("simulation", {}).get("weekly_results", []):
        week = week_data["week"]
        weekly_results[str(week)] = week_data
    
    # Theoretical results (del script anterior)
    theoretical = {
        "Retailer": {
            2: {"inventory": 4.0, "backlog": 0.0, "demand_rate": 4.00, "suggested_order": 8, "orders_placed": 1},
            3: {"inventory": 0.0, "backlog": 4.0, "demand_rate": 6.40, "suggested_order": 24, "orders_placed": 1},
            4: {"inventory": 4.0, "backlog": 0.0, "demand_rate": 5.68, "suggested_order": 14, "orders_placed": 1},
            5: {"inventory": 24.0, "backlog": 0.0, "demand_rate": 5.18, "suggested_order": 0, "orders_placed": 0},
            6: {"inventory": 34.0, "backlog": 0.0, "demand_rate": 4.82, "suggested_order": 0, "orders_placed": 0},
        },
        "Wholesaler": {
            2: {"inventory": 8.0, "backlog": 0.0, "demand_rate": 4.00, "shipments_created": 1},
            3: {"inventory": 0.0, "backlog": 4.0, "demand_rate": 6.40, "shipments_created": 1},
            4: {"inventory": 0.0, "backlog": 10.0, "demand_rate": 5.68, "shipments_created": 1},
            5: {"inventory": 24.0, "backlog": 0.0, "demand_rate": 4.82, "shipments_created": 1},
            6: {"inventory": 45.0, "backlog": 0.0, "demand_rate": 4.00, "shipments_created": 0},
        },
        "Distributor": {
            2: {"inventory": 4.0, "backlog": 0.0, "demand_rate": 4.00, "shipments_created": 1},
            3: {"inventory": 4.0, "backlog": 0.0, "demand_rate": 4.00, "shipments_created": 1},
            4: {"inventory": 0.0, "backlog": 4.0, "demand_rate": 6.40, "shipments_created": 1},
            5: {"inventory": 0.0, "backlog": 13.0, "demand_rate": 5.68, "shipments_created": 1},
            6: {"inventory": 24.0, "backlog": 0.0, "demand_rate": 4.82, "shipments_created": 0},
        },
        "Factory": {
            2: {"inventory": 4.0, "backlog": 0.0, "demand_rate": 4.00, "shipments_created": 1},
            3: {"inventory": 0.0, "backlog": 4.0, "demand_rate": 4.00, "shipments_created": 1},
            4: {"inventory": 0.0, "backlog": 4.0, "demand_rate": 6.40, "shipments_created": 1},
            5: {"inventory": 0.0, "backlog": 17.0, "demand_rate": 5.68, "shipments_created": 1},
            6: {"inventory": 8.0, "backlog": 0.0, "demand_rate": 4.82, "shipments_created": 1},
        }
    }
    
    # Procesar datos para visualización
    comparison_data = {}
    weeks = sorted([int(k) for k in weekly_results.keys()])
    
    for actor in ["Retailer", "Wholesaler", "Distributor", "Factory"]:
        comparison_data[actor] = {
            "weeks": weeks,
            "inventory": {"theoretical": [], "actual": [], "diff": []},
            "backlog": {"theoretical": [], "actual": [], "diff": []},
            "demand_rate": {"theoretical": [], "actual": [], "diff": []},
            "cost": {"theoretical": [], "actual": []}
        }
        
        if actor == "Retailer":
            comparison_data[actor]["suggested_order"] = {"theoretical": [], "actual": [], "diff": []}
        else:
            comparison_data[actor]["shipments_created"] = {"theoretical": [], "actual": [], "diff": []}
        
        for week in weeks:
            if str(week) not in weekly_results or actor not in weekly_results[str(week)]["actors"]:
                continue
                
            actual_data = weekly_results[str(week)]["actors"][actor]
            theo_data = theoretical[actor][week]
            
            # Inventory
            inv_theo = theo_data.get("inventory", 0)
            inv_act = actual_data.get("inventory", 0)
            comparison_data[actor]["inventory"]["theoretical"].append(inv_theo)
            comparison_data[actor]["inventory"]["actual"].append(inv_act)
            comparison_data[actor]["inventory"]["diff"].append(inv_act - inv_theo)
            
            # Backlog
            bl_theo = theo_data.get("backlog", 0)
            bl_act = actual_data.get("backlog", 0)
            comparison_data[actor]["backlog"]["theoretical"].append(bl_theo)
            comparison_data[actor]["backlog"]["actual"].append(bl_act)
            comparison_data[actor]["backlog"]["diff"].append(bl_act - bl_theo)
            
            # Demand rate
            dr_theo = theo_data.get("demand_rate", 0)
            dr_act = actual_data.get("demand_rate", 0)
            comparison_data[actor]["demand_rate"]["theoretical"].append(dr_theo)
            comparison_data[actor]["demand_rate"]["actual"].append(dr_act)
            comparison_data[actor]["demand_rate"]["diff"].append(dr_act - dr_theo)
            
            # Costos (simplificado: inventory * 0.5 + backlog * 1.0)
            cost_theo = (inv_theo * 0.5) + (bl_theo * 1.0)
            cost_act = (inv_act * 0.5) + (bl_act * 1.0)
            comparison_data[actor]["cost"]["theoretical"].append(cost_theo)
            comparison_data[actor]["cost"]["actual"].append(cost_act)
            
            # Métricas específicas
            if actor == "Retailer":
                so_theo = theo_data.get("suggested_order", 0)
                so_act = actual_data.get("suggested_order", 0)
                comparison_data[actor]["suggested_order"]["theoretical"].append(so_theo)
                comparison_data[actor]["suggested_order"]["actual"].append(so_act)
                comparison_data[actor]["suggested_order"]["diff"].append(so_act - so_theo)
            else:
                sc_theo = theo_data.get("shipments_created", 0)
                sc_act = actual_data.get("shipments_created", 0)
                comparison_data[actor]["shipments_created"]["theoretical"].append(sc_theo)
                comparison_data[actor]["shipments_created"]["actual"].append(sc_act)
                comparison_data[actor]["shipments_created"]["diff"].append(sc_act - sc_theo)
    
    return comparison_data, weeks, data['metadata']

def create_dashboard(comparison_data, weeks, metadata, output_file=None):
    """Crea un dashboard completo con múltiples visualizaciones"""
    
    fig = plt.figure(figsize=(20, 12))
    fig.suptitle(f'Beer Game Simulation - {metadata["demand_pattern"].upper()} Pattern\n'
                f'Simulation Date: {metadata["simulation_date"]}', 
                fontsize=16, y=0.98)
    
    # Definir layout del dashboard
    gs = fig.add_gridspec(4, 6, hspace=0.3, wspace=0.3)
    
    actors = ["Retailer", "Wholesaler", "Distributor", "Factory"]
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    # 1. Gráfico de Inventario por Actor (columna 1-4, fila 1)
    ax_inv = fig.add_subplot(gs[0, :4])
    for idx, actor in enumerate(actors):
        ax_inv.plot(weeks, comparison_data[actor]["inventory"]["theoretical"], 
                   '--', color=colors[idx], alpha=0.7, label=f'{actor} (T)')
        ax_inv.plot(weeks, comparison_data[actor]["inventory"]["actual"], 
                   'o-', color=colors[idx], linewidth=2, label=f'{actor} (A)')
    ax_inv.set_title('Inventory - Theoretical vs Actual', fontsize=12)
    ax_inv.set_xlabel('Week')
    ax_inv.set_ylabel('Units')
    ax_inv.legend(ncol=2)
    ax_inv.grid(True, alpha=0.3)
    
    # 2. Gráfico de Backlog por Actor (columna 1-4, fila 2)
    ax_bl = fig.add_subplot(gs[1, :4])
    for idx, actor in enumerate(actors):
        ax_bl.plot(weeks, comparison_data[actor]["backlog"]["theoretical"], 
                  '--', color=colors[idx], alpha=0.7)
        ax_bl.plot(weeks, comparison_data[actor]["backlog"]["actual"], 
                  's-', color=colors[idx], linewidth=2)
    ax_bl.set_title('Backlog - Theoretical vs Actual', fontsize=12)
    ax_bl.set_xlabel('Week')
    ax_bl.set_ylabel('Units')
    ax_bl.grid(True, alpha=0.3)
    
    # 3. Heatmap de Diferencias (columna 5-6, fila 0-2)
    ax_heat = fig.add_subplot(gs[0:2, 4:6])
    
    # Calcular matriz de diferencias totales
    diff_matrix = np.zeros((len(actors), len(weeks)))
    for i, actor in enumerate(actors):
        for j, week in enumerate(weeks):
            # Sumar diferencias absolutas de inventory y backlog
            total_diff = (abs(comparison_data[actor]["inventory"]["diff"][j]) + 
                         abs(comparison_data[actor]["backlog"]["diff"][j]))
            diff_matrix[i, j] = total_diff
    
    im = ax_heat.imshow(diff_matrix, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=40)
    
    # Configurar heatmap
    ax_heat.set_xticks(np.arange(len(weeks)))
    ax_heat.set_yticks(np.arange(len(actors)))
    ax_heat.set_xticklabels(weeks)
    ax_heat.set_yticklabels([a[:3] for a in actors])  # Abreviaturas
    
    # Añadir texto en celdas
    for i in range(len(actors)):
        for j in range(len(weeks)):
            text_color = 'white' if diff_matrix[i, j] > 20 else 'black'
            ax_heat.text(j, i, f'{diff_matrix[i, j]:.1f}',
                       ha='center', va='center', color=text_color, fontweight='bold')
    
    ax_heat.set_title('Total Discrepancy (Inventory + Backlog)', fontsize=12)
    plt.colorbar(im, ax=ax_heat, label='Sum of Differences')
    
    # 4. Costos Acumulados (columna 1-3, fila 3)
    ax_cost = fig.add_subplot(gs[2, :3])
    
    bar_width = 0.35
    x = np.arange(len(actors))
    
    cost_theo = [sum(comparison_data[actor]["cost"]["theoretical"]) for actor in actors]
    cost_act = [sum(comparison_data[actor]["cost"]["actual"]) for actor in actors]
    
    bars1 = ax_cost.bar(x - bar_width/2, cost_theo, bar_width, label='Theoretical', alpha=0.8)
    bars2 = ax_cost.bar(x + bar_width/2, cost_act, bar_width, label='Actual', alpha=0.8)
    
    ax_cost.set_xlabel('Actor')
    ax_cost.set_ylabel('Total Cost ($)')
    ax_cost.set_title('Total Costs by Actor', fontsize=12)
    ax_cost.set_xticks(x)
    ax_cost.set_xticklabels([a[:3] for a in actors])
    ax_cost.legend()
    ax_cost.grid(True, alpha=0.3, axis='y')
    
    # Añadir valores en las barras
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax_cost.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{height:.1f}', ha='center', va='bottom', fontsize=9)
    
    # 5. Efecto Látigo - Variabilidad de Demanda (columna 3-6, fila 2)
    ax_bullwhip = fig.add_subplot(gs[2, 3:])
    
    for idx, actor in enumerate(actors):
        demand_var = []
        for j in range(len(weeks)):
            # Calcular variabilidad como desviación del teórico
            var = abs(comparison_data[actor]["demand_rate"]["diff"][j])
            demand_var.append(var)
        ax_bullwhip.plot(weeks, demand_var, 'o-', color=colors[idx], 
                        linewidth=2, label=actor)
    
    ax_bullwhip.set_title('Bullwhip Effect - Demand Variability', fontsize=12)
    ax_bullwhip.set_xlabel('Week')
    ax_bullwhip.set_ylabel('Demand Deviation from Theoretical')
    ax_bullwhip.legend()
    ax_bullwhip.grid(True, alpha=0.3)
    
    # 6. Diferencias por Actor (columna 4-6, fila 3)
    ax_diff = fig.add_subplot(gs[3, :])
    
    diff_categories = ['Inventory', 'Backlog', 'Demand Rate']
    actor_positions = np.arange(len(actors))
    
    for i, category in enumerate(diff_categories):
        category_diffs = []
        for actor in actors:
            # Calcular diferencia promedio absoluta
            if category == 'Inventory':
                diffs = comparison_data[actor]["inventory"]["diff"]
            elif category == 'Backlog':
                diffs = comparison_data[actor]["backlog"]["diff"]
            else:  # Demand Rate
                diffs = comparison_data[actor]["demand_rate"]["diff"]
            
            avg_diff = np.mean([abs(d) for d in diffs])
            category_diffs.append(avg_diff)
        
        # Barras agrupadas
        pos = actor_positions + (i - 1) * 0.25
        ax_diff.bar(pos, category_diffs, width=0.2, 
                   label=category, alpha=0.8)
    
    ax_diff.set_xlabel('Actor')
    ax_diff.set_ylabel('Average Absolute Difference')
    ax_diff.set_title('Model Discrepancy Analysis', fontsize=12)
    ax_diff.set_xticks(actor_positions)
    ax_diff.set_xticklabels(actors)
    ax_diff.legend()
    ax_diff.grid(True, alpha=0.3, axis='y')
    
    # Ajustar layout
    plt.tight_layout()
    
    # Guardar si se especifica archivo
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Dashboard guardado como: {output_file}")
    
    return fig

def create_individual_plots(comparison_data, weeks, metadata, output_prefix="beer_game"):
    """Crea gráficos individuales para cada actor"""
    
    actors = ["Retailer", "Wholesaler", "Distributor", "Factory"]
    
    for actor in actors:
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle(f'{actor} - Detailed Analysis\n'
                    f'Demand Pattern: {metadata["demand_pattern"]}', fontsize=14)
        
        # Gráfico 1: Inventory vs Backlog
        ax1 = axes[0, 0]
        week_idx = np.arange(len(weeks))
        width = 0.35
        
        bars1 = ax1.bar(week_idx - width/2, comparison_data[actor]["inventory"]["theoretical"], 
                       width, label='Inventory (T)', alpha=0.7, color='skyblue')
        bars2 = ax1.bar(week_idx + width/2, comparison_data[actor]["inventory"]["actual"], 
                       width, label='Inventory (A)', alpha=0.7, color='blue')
        
        # Línea de backlog
        ax1b = ax1.twinx()
        ax1b.plot(week_idx, comparison_data[actor]["backlog"]["theoretical"], 'r--', 
                 label='Backlog (T)', alpha=0.7)
        ax1b.plot(week_idx, comparison_data[actor]["backlog"]["actual"], 'ro-', 
                 label='Backlog (A)', alpha=0.7)
        
        ax1.set_xlabel('Week')
        ax1.set_ylabel('Inventory (units)')
        ax1b.set_ylabel('Backlog (units)')
        ax1.set_title(f'{actor} - Inventory & Backlog')
        ax1.set_xticks(week_idx)
        ax1.set_xticklabels(weeks)
        
        # Combinar leyendas
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax1b.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        # Gráfico 2: Demand Rate
        ax2 = axes[0, 1]
        ax2.plot(weeks, comparison_data[actor]["demand_rate"]["theoretical"], 
                'g--o', label='Theoretical', linewidth=2, alpha=0.7)
        ax2.plot(weeks, comparison_data[actor]["demand_rate"]["actual"], 
                'g-s', label='Actual', linewidth=2, alpha=0.7)
        ax2.fill_between(weeks, 
                        comparison_data[actor]["demand_rate"]["theoretical"],
                        comparison_data[actor]["demand_rate"]["actual"],
                        alpha=0.2, color='green')
        
        ax2.set_xlabel('Week')
        ax2.set_ylabel('Demand Rate')
        ax2.set_title(f'{actor} - Demand Rate Comparison')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Gráfico 3: Diferencias
        ax3 = axes[1, 0]
        metrics_to_plot = []
        diff_data = []
        
        metrics_to_plot.append('Inventory')
        diff_data.append(comparison_data[actor]["inventory"]["diff"])
        
        metrics_to_plot.append('Backlog')
        diff_data.append(comparison_data[actor]["backlog"]["diff"])
        
        metrics_to_plot.append('Demand Rate')
        diff_data.append(comparison_data[actor]["demand_rate"]["diff"])
        
        if actor == "Retailer":
            metrics_to_plot.append('Suggested Order')
            diff_data.append(comparison_data[actor]["suggested_order"]["diff"])
        else:
            metrics_to_plot.append('Shipments')
            diff_data.append(comparison_data[actor]["shipments_created"]["diff"])
        
        colors = ['blue', 'red', 'green', 'purple']
        for i, (metric, diffs) in enumerate(zip(metrics_to_plot, diff_data)):
            bars = ax3.bar(np.arange(len(weeks)) + i*0.2, diffs, width=0.2, 
                          label=metric, color=colors[i], alpha=0.7)
            
            # Añadir etiquetas para diferencias grandes
            for j, diff in enumerate(diffs):
                if abs(diff) >= 2.0:
                    ax3.text(j + i*0.2, diff + (0.1 if diff >=0 else -0.5), 
                            f'{diff:.1f}', ha='center', va='bottom' if diff >=0 else 'top',
                            fontsize=8, color='red')
        
        ax3.set_xlabel('Week')
        ax3.set_ylabel('Difference (Actual - Theoretical)')
        ax3.set_title(f'{actor} - Differences by Metric')
        ax3.set_xticks(np.arange(len(weeks)) + 0.3)
        ax3.set_xticklabels(weeks)
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis='y')
        
        # Gráfico 4: Costos semanales
        ax4 = axes[1, 1]
        x = np.arange(len(weeks))
        width = 0.35
        
        cost_theo = comparison_data[actor]["cost"]["theoretical"]
        cost_act = comparison_data[actor]["cost"]["actual"]
        
        bars1 = ax4.bar(x - width/2, cost_theo, width, label='Theoretical', 
                       alpha=0.7, color='lightgray')
        bars2 = ax4.bar(x + width/2, cost_act, width, label='Actual', 
                       alpha=0.7, color='darkgray')
        
        # Añadir valores
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax4.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                            f'{height:.1f}', ha='center', va='bottom', fontsize=8)
        
        ax4.set_xlabel('Week')
        ax4.set_ylabel('Cost ($)')
        ax4.set_title(f'{actor} - Weekly Costs')
        ax4.set_xticks(x)
        ax4.set_xticklabels(weeks)
        ax4.legend()
        ax4.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(f'{output_prefix}_{actor.lower()}.png', dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Gráfico individual guardado: {output_prefix}_{actor.lower()}.png")

def main():
    if len(sys.argv) < 2:
        print("Usage: python beer_game_visualizer.py <json_report_file> [--individual]")
        print("Example: python beer_game_visualizer.py beer_game_report_20260110_190738.json")
        print("         python beer_game_visualizer.py beer_game_report_20260110_190738.json --individual")
        sys.exit(1)
    
    json_file = sys.argv[1]
    create_individual = '--individual' in sys.argv
    
    try:
        # Cargar y procesar datos
        print(f"📊 Cargando datos de {json_file}...")
        comparison_data, weeks, metadata = load_and_compare_data(json_file)
        
        # Crear dashboard principal
        print("🎨 Generando dashboard principal...")
        fig = create_dashboard(comparison_data, weeks, metadata, 
                              output_file=f"beer_game_dashboard_{metadata['simulation_date'][:10]}.png")
        
        # Crear gráficos individuales si se solicita
        if create_individual:
            print("📈 Generando gráficos individuales por actor...")
            create_individual_plots(comparison_data, weeks, metadata,
                                  output_prefix=f"beer_game_{metadata['simulation_date'][:10]}")
        
        print("\n" + "="*60)
        print("✅ Visualizaciones completadas exitosamente!")
        print("="*60)
        print("\nArchivos generados:")
        print(f"  • beer_game_dashboard_{metadata['simulation_date'][:10]}.png")
        if create_individual:
            print(f"  • beer_game_{metadata['simulation_date'][:10]}_retailer.png")
            print(f"  • beer_game_{metadata['simulation_date'][:10]}_wholesaler.png")
            print(f"  • beer_game_{metadata['simulation_date'][:10]}_distributor.png")
            print(f"  • beer_game_{metadata['simulation_date'][:10]}_factory.png")
        
        # Mostrar resumen de diferencias
        print("\n📋 Resumen de diferencias (promedio absoluto):")
        print("-" * 50)
        for actor in ["Retailer", "Wholesaler", "Distributor", "Factory"]:
            inv_diff = np.mean([abs(d) for d in comparison_data[actor]["inventory"]["diff"]])
            bl_diff = np.mean([abs(d) for d in comparison_data[actor]["backlog"]["diff"]])
            dr_diff = np.mean([abs(d) for d in comparison_data[actor]["demand_rate"]["diff"]])
            
            print(f"{actor:12} | Inv: {inv_diff:6.2f} | Backlog: {bl_diff:6.2f} | Demand: {dr_diff:6.2f}")
        
        # Mostrar el dashboard
        plt.show()
        
    except FileNotFoundError:
        print(f"❌ Error: Archivo no encontrado: {json_file}")
    except json.JSONDecodeError:
        print(f"❌ Error: Archivo JSON inválido: {json_file}")
    except KeyError as e:
        print(f"❌ Error: Estructura de datos inesperada. Clave faltante: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    main()