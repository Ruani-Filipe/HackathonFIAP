from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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
    ],
    "api": [
        {
            "category": "S",
            "threat": "Sequestro de credenciais/tokens e chamadas se passando por cliente legítimo.",
            "mitigation": "OAuth2/OIDC, mTLS, rotação de chaves, tokens curtos, validação de audience/issuer.",
        },
        {
            "category": "T",
            "threat": "Manipulação de parâmetros/payload (injeção, alteração de campos sensíveis).",
            "mitigation": "Validação de schema, allowlist, WAF, normalização, proteção contra injeção (SQL/NoSQL/OS).",
        },
        {
            "category": "R",
            "threat": "Requisições sem trilha de auditoria e sem correlação ponta-a-ponta.",
            "mitigation": "Logs com request-id/trace-id, auditoria de endpoints críticos, retenção e imutabilidade.",
        },
        {
            "category": "I",
            "threat": "Exposição de dados sensíveis em respostas/erros ou via endpoints indevidos.",
            "mitigation": "Masking, classificação de dados, controles de acesso, headers seguros, evitar verbose errors.",
        },
        {
            "category": "D",
            "threat": "DoS por abuso de endpoints (flood, payload grande, consultas custosas).",
            "mitigation": "Rate limit, quotas, timeouts, circuit breaker, caching, limites de payload, proteção DDoS.",
        },
        {
            "category": "E",
            "threat": "Bypass de autorização (Broken Access Control) elevando privilégio via API.",
            "mitigation": "Autorização por recurso/ação, checagem server-side, testes de permissão, least privilege.",
        },
    ],
    "database": [
        {
            "category": "S",
            "threat": "Acesso ao banco usando identidade/credencial indevida.",
            "mitigation": "Segredos em vault, rotação, IAM/roles, MFA no admin, credenciais por serviço (não compartilhadas).",
        },
        {
            "category": "T",
            "threat": "Alteração não autorizada de dados (corrupção, update/delete indevidos).",
            "mitigation": "Controles de integridade, constraints, trilhas de auditoria, backups e point-in-time recovery.",
        },
        {
            "category": "R",
            "threat": "Operações sem auditoria (sem evidência de quem alterou o quê).",
            "mitigation": "DB audit logs, trilha imutável, correlação com identidade da aplicação, retenção.",
        },
        {
            "category": "I",
            "threat": "Vazamento de dados por permissões excessivas ou falta de criptografia.",
            "mitigation": "Least privilege, criptografia em repouso, KMS, masking/tokenização, segregação por schema.",
        },
        {
            "category": "D",
            "threat": "Indisponibilidade por consultas pesadas, lock, saturação de conexões.",
            "mitigation": "Limites de conexão, pool, índices, réplicas, tuning, timeouts, proteção contra queries abusivas.",
        },
        {
            "category": "E",
            "threat": "Elevação de privilégio no banco (roles indevidas, grants abertos).",
            "mitigation": "Revisão de grants, roles mínimas, separação de funções, hardening e monitoramento de privilégios.",
        },
    ],
    "queue": [
        {
            "category": "S",
            "threat": "Produtor/consumidor não autorizado publicando/consumindo mensagens.",
            "mitigation": "AuthN/AuthZ por tópico/fila, credenciais por serviço, mTLS quando aplicável.",
        },
        {
            "category": "T",
            "threat": "Manipulação do conteúdo da mensagem ou headers.",
            "mitigation": "Assinatura/HMAC, validação de schema, idempotência, checks de integridade.",
        },
        {
            "category": "R",
            "threat": "Dificuldade de rastrear quem publicou/consumiu uma mensagem.",
            "mitigation": "Trace-id/correlation-id, logs do broker, auditoria de publish/consume.",
        },
        {
            "category": "I",
            "threat": "Mensagens com dados sensíveis sem proteção.",
            "mitigation": "Criptografia em trânsito, criptografia de payload, minimização de dados, retenção controlada.",
        },
        {
            "category": "D",
            "threat": "Fila travada por backlog, poison messages, reprocessamento infinito.",
            "mitigation": "DLQ, retries com backoff, limites de tamanho, quotas, monitoramento e autoscaling de consumers.",
        },
        {
            "category": "E",
            "threat": "Escalada via mensagens privilegiadas (comandos administrativos).",
            "mitigation": "Separar tópicos privilegiados, autorização estrita, validação do emissor, allowlist de comandos.",
        },
    ],
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


def infer_node_type(label: str | None) -> str:
    """Infer a coarse component type from label text using keyword matching."""
    t = (label or "").strip().lower()
    if not t:
        return "component"

    # --- users / actors ---
    if any(k in t for k in ["user", "usuário", "usuario", "customer", "cliente", "browser", "mobile", "frontend", "ui"]):
        return "user"

    # --- network / edge ---
    if any(k in t for k in ["cdn", "cloudfront", "akamai"]):
        return "cdn"
    if any(k in t for k in ["waf", "firewall"]):
        return "waf"
    if any(k in t for k in ["load balancer", "elb", "alb", "nlb", "ingress", "reverse proxy", "proxy"]):
        return "load_balancer"
    if any(k in t for k in ["dns", "route 53", "route53"]):
        return "dns"

    # --- api / gateway ---
    if any(k in t for k in ["api gateway", "gateway", "endpoint", "rest", "graphql"]):
        return "api_gateway"
    if "api" in t:
        return "api"

    # --- compute / apps ---
    if any(k in t for k in ["service", "microservice", "backend", "worker", "lambda", "function", "container", "pod"]):
        return "service"
    if any(k in t for k in ["server", "vm", "ec2", "instance", "app server", "web server", "nginx", "apache"]):
        return "server"

    # --- data ---
    if any(k in t for k in ["db", "database", "rds", "dynamodb", "postgres", "mysql", "sql server", "oracle", "mongo", "redis"]):
        return "database"
    if any(k in t for k in ["cache", "memcached"]):
        return "cache"
    if any(k in t for k in ["s3", "bucket", "storage", "blob", "files", "minio"]):
        return "storage"

    # --- messaging ---
    if any(k in t for k in ["queue", "mq", "kafka", "sqs", "pubsub", "rabbit", "event", "topic", "stream"]):
        return "queue"

    # --- auth / identity ---
    if any(k in t for k in ["auth", "oauth", "oidc", "sso", "iam", "identity", "cognito", "keycloak"]):
        return "identity"

    # --- observability ---
    if any(k in t for k in ["cloudtrail", "siem", "log", "logging", "monitor", "grafana", "prometheus"]):
        return "observability"

    return "component"


def _load_stride_kb() -> dict[str, Any]:
    kb_path = Path("kb") / "stride_kb.json"
    if not kb_path.exists():
        return {}
    return json.loads(kb_path.read_text(encoding="utf-8"))


def _kb_refs(kb: dict[str, Any], scope: str, stride: str) -> list[dict[str, Any]]:
    return list(((kb.get(scope) or {}).get(stride) or {}).get("references") or [])


def build_stride_threats(architecture: dict[str, Any]) -> dict[str, Any]:
    """Build STRIDE threats for nodes and edges in the architecture."""
    items: list[dict[str, Any]] = []
    kb = _load_stride_kb()

    def _should_emit(rule: dict[str, str], *, node: dict[str, Any] | None = None) -> bool:
        """Return True only when there is a plausible trigger for this STRIDE category."""
        if not node:
            return True

        label = str(node.get("label") or "").lower()
        t = str(node.get("type") or "component")

        # If we couldn't infer anything useful, avoid pretending we know all threats.
        if t == "component" and (not label or label == "component"):
            return False

        s = rule["category"]

        if s == "S":
            return any(k in label for k in ["auth", "oauth", "oidc", "login", "token", "iam", "identity", "cognito"])
        if s == "T":
            return t in {"api", "database", "queue", "cache", "storage"} or any(
                k in label for k in ["api", "service", "db", "database", "queue", "storage", "gateway"]
            )
        if s == "R":
            return t in {"observability"} or any(k in label for k in ["log", "audit", "cloudtrail", "siem", "monitor"])
        if s == "I":
            return t in {"database", "storage", "cache"} or any(
                k in label for k in ["db", "database", "storage", "bucket", "s3", "blob", "pii", "secret"]
            )
        if s == "D":
            return t in {"api", "queue"} or any(k in label for k in ["api", "gateway", "queue", "service"])
        if s == "E":
            return t in {"api", "identity"} or any(k in label for k in ["admin", "iam", "role", "policy", "auth", "oauth", "oidc"])

        return True

    # Node threats
    for n in architecture.get("nodes", []):
        node_type = str(n.get("type") or "component")
        if node_type == "component":
            node_type = infer_node_type(n.get("label"))
            n["type"] = node_type

        rules = NODE_RULES.get(node_type, NODE_RULES["component"])
        for r in rules:
            if not _should_emit(r, node=n):
                continue
            items.append(
                {
                    "scope": "node",
                    "target_id": n.get("id"),
                    "target_label": n.get("label"),
                    "target_type": node_type,
                    "stride": r["category"],
                    "threat": r["threat"],
                    "mitigation": r["mitigation"],
                    "references": _kb_refs(kb, "component", r["category"]),
                    "evidence": {"bbox": n.get("bbox"), "page": n.get("page"), "score": n.get("score")},
                }
            )

    # Edge threats
    for e in architecture.get("edges", []):
        edge_label = f"{e.get('source')} -> {e.get('target')}"
        for r in EDGE_RULES:
            if not _should_emit(r, node={"label": edge_label, "type": "flow"}):
                continue
            items.append(
                {
                    "scope": "edge",
                    "target_id": e.get("id"),
                    "from": e.get("source"),
                    "to": e.get("target"),
                    "stride": r["category"],
                    "threat": r["threat"],
                    "mitigation": r["mitigation"],
                    "references": _kb_refs(kb, "flow", r["category"]),
                }
            )

    return {"run_id": architecture.get("run_id"), "items": items}
