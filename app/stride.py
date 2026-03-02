from __future__ import annotations

from typing import Any


# Minimal STRIDE knowledge base for MVP.
# In a real system, move to YAML/JSON and enrich with CWE/ASVS references.
NODE_RULES: dict[str, list[dict[str, str]]] = {
    "component": [
        {
            "category": "S",
            "threat": "Spoofing de identidade do componente/serviço.",
            "mitigation": "Autenticação forte entre serviços (mTLS/OIDC), rotação de segredos, validação de identidade.",
        },
        {
            "category": "T",
            "threat": "Adulteração de dados em trânsito/armazenamento.",
            "mitigation": "TLS ponta-a-ponta, assinatura/integração de mensagens, controles de integridade, WORM/auditoria.",
        },
        {
            "category": "R",
            "threat": "Repúdio (ações sem trilha de auditoria).",
            "mitigation": "Logging centralizado e imutável, correlação (trace-id), relógio sincronizado (NTP), retenção.",
        },
        {
            "category": "I",
            "threat": "Divulgação de informação sensível.",
            "mitigation": "Criptografia em repouso, mascaramento, segregação, least privilege, gestão de chaves (KMS).",
        },
        {
            "category": "D",
            "threat": "Negação de serviço (indisponibilidade).",
            "mitigation": "Rate limit, circuit breaker, autoscaling, filas, caching, proteção DDoS.",
        },
        {
            "category": "E",
            "threat": "Elevação de privilégio.",
            "mitigation": "RBAC/ABAC, hardening, execução com menor privilégio, validação de autorização em cada ação.",
        },
    ]
}

EDGE_RULES: list[dict[str, str]] = [
    {
        "category": "S",
        "threat": "Spoofing no canal (cliente/serviço se passando por outro).",
        "mitigation": "TLS/mTLS, OAuth2/OIDC, validação de certificados, pinning (quando aplicável).",
    },
    {
        "category": "T",
        "threat": "Tampering no tráfego (alteração de payload).",
        "mitigation": "TLS, assinaturas (HMAC/JWS), checksums, validação de schema.",
    },
    {
        "category": "R",
        "threat": "Repúdio em transações (sem evidência do request).",
        "mitigation": "Logs com request-id, nonces, auditoria, armazenamento imutável.",
    },
    {
        "category": "I",
        "threat": "Information disclosure no tráfego (vazamento de credenciais/dados).",
        "mitigation": "TLS forte, minimização de dados, headers seguros, secrets vault, tokenização.",
    },
    {
        "category": "D",
        "threat": "DoS no canal (flood, exaustão de recursos).",
        "mitigation": "Rate limit, WAF, timeouts, quotas, backpressure.",
    },
    {
        "category": "E",
        "threat": "Elevação de privilégio via endpoints expostos/má configuração.",
        "mitigation": "Autorização estrita, validação de escopo, políticas de egress/ingress, hardening.",
    },
]


def build_stride_threats(architecture: dict[str, Any]) -> dict[str, Any]:
    """
    Input:
      architecture = { nodes: [...], edges: [...] }
    Output:
      { items: [ ...threat entries... ] }
    """
    items: list[dict[str, Any]] = []

    # Node threats
    for n in architecture.get("nodes", []):
        node_type = str(n.get("type") or "component")
        rules = NODE_RULES.get(node_type, NODE_RULES["component"])
        for r in rules:
            items.append(
                {
                    "scope": "node",
                    "target_id": n.get("id"),
                    "target_label": n.get("label"),
                    "target_type": node_type,
                    "stride": r["category"],
                    "threat": r["threat"],
                    "mitigation": r["mitigation"],
                    "evidence": {"bbox": n.get("bbox"), "page": n.get("page"), "score": n.get("score")},
                }
            )

    # Edge threats
    for e in architecture.get("edges", []):
        for r in EDGE_RULES:
            items.append(
                {
                    "scope": "edge",
                    "target_id": e.get("id"),
                    "from": e.get("from"),
                    "to": e.get("to"),
                    "stride": r["category"],
                    "threat": r["threat"],
                    "mitigation": r["mitigation"],
                }
            )

    return {"run_id": architecture.get("run_id"), "items": items}
