import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
from datetime import datetime, timedelta

def generate_performance_chart(daily_stats, system_info=None):
    """
    Generates a performance chart from a list of daily stats.
    daily_stats: list of dicts 
    system_info: optional dict with current system stats
    Returns: BytesIO object containing the PNG image.
    """
    if not daily_stats:
        daily_stats = [{'date': datetime.now().strftime('%Y-%m-%d'), 'forwards': 0, 'failures': 0, 'system_load_sum': 0, 'system_load_count': 0}]
        
    dates = [datetime.strptime(d['date'], '%Y-%m-%d').strftime('%d/%m') for d in daily_stats]
    forwards = [d['forwards'] for d in daily_stats]
    failures = [d['failures'] for d in daily_stats]
    
    # Calculate average system load per day
    sys_loads = []
    for d in daily_stats:
        if d.get('system_load_count', 0) > 0:
            sys_loads.append(d['system_load_sum'] / d['system_load_count'])
        else:
            sys_loads.append(0)
    
    # Use light theme
    plt.style.use('seaborn-v0_8-whitegrid')
    
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    # Plot Message Counts (Left Axis)
    ax1.set_xlabel("Date", fontsize=10)
    ax1.set_ylabel("Message Count", fontsize=10, color='#333333')
    line1 = ax1.plot(dates, forwards, marker='o', linestyle='-', color='#00a65a', label='Success', linewidth=2)
    line2 = ax1.plot(dates, failures, marker='x', linestyle='--', color='#dd4b39', label='Failures', linewidth=2)
    ax1.tick_params(axis='y', labelcolor='#333333')
    
    # Plot System Load (Right Axis)
    ax2 = ax1.twinx()
    ax2.set_ylabel("Sys Load %", fontsize=10, color='#0073b7')
    line3 = ax2.plot(dates, sys_loads, marker='.', linestyle=':', color='#0073b7', label='System Load', linewidth=2)
    ax2.tick_params(axis='y', labelcolor='#0073b7')
    ax2.set_ylim(0, 100) # Percentage scale
    
    # Combine legends
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', frameon=True, framealpha=0.9)
    
    # Title
    plt.title("Forward Performance (Last 7 Days)", fontsize=14, pad=10, fontweight='bold')
    
    # Add System Info Box if provided
    if system_info:
        info_text = (
            f"CPU: {system_info.get('cpu', 'N/A')}% | "
            f"RAM: {system_info.get('ram_used', 'N/A')}MB | "
            f"Temp: {system_info.get('temp', 'N/A')}"
        )
        props = dict(boxstyle='round', facecolor='#f4f4f4', alpha=0.9, edgecolor='#cccccc')
        ax1.text(0.98, 0.98, info_text, transform=ax1.transAxes, fontsize=9,
                verticalalignment='top', horizontalalignment='right', bbox=props)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()
    
    return buf
