package infrastructure

import future.keywords.if
import future.keywords.contains

default allow := false

allow if {
    disk_ok
    cpu_ok
    memory_ok
}

disk_ok if {
    input.host.disk_free_gb >= input.thresholds.min_disk_free_gb
}

cpu_ok if {
    input.host.cpu_load_percent <= input.thresholds.max_cpu_load
}

memory_ok if {
    input.host.memory_free_percent >= input.thresholds.min_memory_free_percent
}

violations contains msg if {
    not disk_ok
    msg := sprintf(
        "Disk free %vGB is below minimum %vGB",
        [input.host.disk_free_gb, input.thresholds.min_disk_free_gb]
    )
}

violations contains msg if {
    not cpu_ok
    msg := sprintf(
        "CPU load %v%% exceeds maximum %v%%",
        [input.host.cpu_load_percent, input.thresholds.max_cpu_load]
    )
}

violations contains msg if {
    not memory_ok
    msg := sprintf(
        "Memory free %v%% is below minimum %v%%",
        [input.host.memory_free_percent, input.thresholds.min_memory_free_percent]
    )
}