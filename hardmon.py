import os
import time
import json
import sys
import subprocess
import shutil

LAST_ENERGY_READING = None
IS_AMDGPU = os.path.exists("/sys/kernel/debug/dri/0/amdgpu_pm_info")
IS_NVGPU = os.path.exists("/dev/nvidia0")
if IS_NVGPU:
    NVSMI = shutil.which('nvidia-smi')
    smiparams = [
        "clocks.current.graphics",
        "clocks.current.memory",
        "clocks.current.video",
        "temperature.gpu",
        "temperature.memory",
        "power.draw",
        "power.limit",
        "utilization.gpu",
        "utilization.memory"
    ]
    params = [
        "clocks.gpu.graphics",
        "clocks.gpu.memory",
        "clocks.gpu.video",
        "gpu_temp",
        "temperature.memory",
        "average_gpu",
        "power.limit",
        "gpu_load",
        "vram_load"
    ]

    qs = ",".join(smiparams)
    smiqgpu = f"--query-gpu={qs}"

def get_nvidia_stats():
    if not NVSMI: return False
    process = subprocess.run(
        [ NVSMI, smiqgpu, "--format=csv" ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out = process.stdout.decode()
    lines = out.split("\n")
    headers = lines[0].split(",")
    values = lines[1].split(",")
    stats = {}
    for i, _ in enumerate(smiparams):
        stats[params[i]] = values[i]
    return stats

def get_radeon_stats():
    with open("/sys/kernel/debug/dri/0/amdgpu_pm_info") as amdgpu_info:
        amdgpu_stats = amdgpu_info.readlines()
    in_clocks_section = True
    stats = {}
    for line in amdgpu_stats:
        line = line.strip("\n")
        if not line:
            in_clocks_section = False
        if in_clocks_section and line.startswith("\t"):
            value, unit, key = line.split(maxsplit=2)
            key = key.strip("()").replace(" ", "_").lower()
            stats[key] = " ".join((value, unit))
        if line.startswith("GPU Temperature"):
            stats["gpu_temp"] = line.split(":")[1].strip()
        if line.startswith("GPU Load"):
            stats["gpu_load"] = line.split(":")[1].strip()
        if line.startswith("MEM Load"):
            stats["vram_load"] = line.split(":")[1].strip()
    return stats


def get_cpu_stats():
    global LAST_ENERGY_READING
    cpu_stats = {}
    with open("/proc/cpuinfo") as cpu_info:
        cpu_info_contents = cpu_info.readlines()
    current_cpu = 0
    for line in cpu_info_contents:
        line = line.strip("\n")
        if line.startswith("processor"):
            current_cpu = line.split(":")[1].strip()
        if line.startswith("cpu MHz"):
            cpu_stats["cpu%s_clk" % current_cpu] = line.split(":")[1].strip()
    with open("/sys/class/hwmon/hwmon1/temp1_input") as cpu_temp_file:
        cpu_stats["cpu_temp"] = int(cpu_temp_file.read().strip()) / 1000
    with open("/proc/loadavg") as cpu_load_file:
        cpu_stats["cpu_load"] = cpu_load_file.read().split()[0]
    try:
        with open("/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj") as cpu_energy:
            current_energy = int(cpu_energy.read().strip())
            if LAST_ENERGY_READING:
                # convert to uj/s then to Watts
                cpu_stats["cpu_power"] = (current_energy - LAST_ENERGY_READING) / 1000000
            LAST_ENERGY_READING = current_energy
    except OSError:
        pass
    return cpu_stats


def get_mem_stats():
    stats = {}
    mem_total = 0
    with open("/proc/meminfo") as meminfo:
        for line in meminfo.readlines():
            if line.startswith("MemTotal"):
                mem_total = int(line.split()[1])
            if line.startswith("MemAvailable"):
                stats["mem_available"] = int(line.split()[1])
    stats["mem_used"] = mem_total - stats["mem_available"]
    return stats


def collect_hw_stats():
    stats = {"time": int(time.time())}
    if IS_AMDGPU:
        stats.update(get_radeon_stats())
    if IS_NVGPU:
        stats.update(get_nvidia_stats())
    stats.update(get_cpu_stats())
    stats.update(get_mem_stats())
    return stats


if __name__ == "__main__":
    while True:
        sys.stdout.write(json.dumps(collect_hw_stats()))
        sys.stdout.write("\n")
        time.sleep(1)