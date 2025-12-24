from datetime import datetime
import psutil
import os

def get_system_resources():
    """
    Returns a dictionary with system resource usage.
    """
    cpu_percent = psutil.cpu_percent(interval=None)
    
    mem = psutil.virtual_memory()
    ram_used = mem.used / (1024 * 1024) # MB
    ram_total = mem.total / (1024 * 1024) # MB
    ram_percent = mem.percent
    
    return {
        "cpu": cpu_percent,
        "ram_used": f"{ram_used:.0f}",
        "ram_total": f"{ram_total:.0f}",
        "ram_percent": ram_percent
    }

def get_bot_resources():
    """
    Returns a dictionary with Bot process resource usage.
    """
    process = psutil.Process()
    # CPU usage since last call, divided by vCPUs if you want normalized, 
    # but standard 'top' behavior is usually total % across threads
    cpu_percent = process.cpu_percent(interval=None) 
    
    mem_info = process.memory_info()
    ram_used = mem_info.rss / (1024 * 1024) # MB RSS (Resident Set Size)
    
    return {
        "cpu": cpu_percent,
        "ram_used": f"{ram_used:.1f}"
    }

def get_cpu_temperature():
    """
    Returns CPU temperature in Celsius.
    Attempts multiple methods to read temperature.
    """
    try:
        temps = psutil.sensors_temperatures()
        
        if 'coretemp' in temps:
            temp_list = temps['coretemp']
            if temp_list:
                avg_temp = sum(t.current for t in temp_list) / len(temp_list)
                return f"{avg_temp:.1f}°C"
        
        elif 'k10temp' in temps:
            temp_list = temps['k10temp']
            if temp_list:
                return f"{temp_list[0].current:.1f}°C"
        
        elif 'cpu_thermal' in temps:
            temp_list = temps['cpu_thermal']
            if temp_list:
                return f"{temp_list[0].current:.1f}°C"
        
        for sensor_name, temp_list in temps.items():
            if temp_list:
                return f"{temp_list[0].current:.1f}°C"
        
        return "N/A"
    except (AttributeError, KeyError):
        return "N/A"
    except Exception:
        return "N/A"
