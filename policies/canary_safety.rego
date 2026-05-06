package canary_safety

import future.keywords.if
import future.keywords.contains

default allow := false

allow if {
    error_rate_ok
    latency_ok
}

error_rate_ok if {
    input.metrics.error_rate <= input.thresholds.max_error_rate
}

latency_ok if {
    input.metrics.p99_latency_ms <= input.thresholds.max_p99_latency_ms
}

violations contains msg if {
    not error_rate_ok
    pct := input.metrics.error_rate * 100
    threshold_pct := input.thresholds.max_error_rate * 100
    msg := sprintf(
        "Error rate %v%% exceeds maximum %v%%",
        [pct, threshold_pct]
    )
}

violations contains msg if {
    not latency_ok
    msg := sprintf(
        "P99 latency %vms exceeds maximum %vms",
        [input.metrics.p99_latency_ms, input.thresholds.max_p99_latency_ms]
    )
}