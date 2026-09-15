from scripts.cm_benchmark_runpod_readiness import sanitize_cpu_catalog, sanitize_gpu_offer, sanitize_inventory


def test_inventory_is_sanitized_and_hashed():
    result = sanitize_inventory([{"id": "secret-id", "name": "private", "desiredStatus": "RUNNING"}])
    assert result["pod_count"] == 1
    assert result["status_counts"] == {"RUNNING": 1}
    assert "secret-id" not in str(result)
    assert result["pod_identifiers_recorded"] is False


def test_cpu_catalog_selects_64_gb_offer():
    rows = sanitize_cpu_catalog({"cpus": [{
        "id": "cpu3g", "name": "General Purpose", "availability": "HIGH",
        "ramGbPerVcpu": 4, "vcpu": {"min": 2, "max": 32},
        "price": {"securePerVcpu": 0.04},
        "dataCenters": [{"id": "EU-RO-1", "availability": "HIGH"}],
    }]})
    assert rows[0]["eligible"] is True
    assert rows[0]["ram_gb"] == 64
    assert rows[0]["secure_usd_per_hour"] == 0.64


def test_gpu_offer_is_catalog_only():
    result = sanitize_gpu_offer({
        "id": "NVIDIA GeForce RTX 3090", "name": "RTX 3090",
        "availability": "MEDIUM", "price": {"secure": 0.5},
    })
    assert result["catalog_eligible"] is True
    assert result["advertised_ram_gb"] == 125
