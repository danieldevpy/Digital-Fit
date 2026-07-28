# SPEC-011 — API SaaS (Auth, Quotas, Planos)
Status: draft | Camada: api (Django) | Depende de: SPEC-009, SPEC-010

## Entidade e responsabilidade

A casca de produto: contas, autenticação, quotas por plano e as telas de negócio. Deliberadamente a ÚLTIMA camada — todo o núcleo funciona anônimo e por eventos, então o SaaS é adicionado por fora, sem tocar o pipeline.

## Fase Inicial (entra na Fase 1 do roadmap)

### Escopo / Comportamento

- Auth por e-mail+senha com JWT curto + refresh (SimpleJWT). Sessões anônimas continuam permitidas (trial: 3 sessões/dia por device-id, sem cartão, sem cadastro — o funil do produto).
- `Session` ganha `user_id` opcional; histórico só para logados.
- Endpoints: `POST /auth/register|login|refresh`, `GET /me`, `GET /sessions?mine`, `GET /sessions/{id}/report`.
- CORS/HTTPS prontos para o domínio; rate limit básico por IP (django-ratelimit) nas rotas de auth.

### Fora de escopo (vai para Evolução)

Pagamentos, planos pagos, equipe/professor, OAuth social, LGPD tooling.

### Critérios de aceite

1. Trial anônimo: 4ª sessão do dia no mesmo device é negada com mensagem de upgrade/cadastro.
2. Usuário logado vê histórico só dele; relatório de sessão alheia → 404.
3. Tokens expirados renovam sem derrubar sessão de treino em andamento.

## Fase Evolução

- **Planos**: Free (N sessões/dia, edge only) · Pro (mais sessões, prioridade de fila, acesso cloud, histórico completo). Enforcement via quotas da SPEC-009.
- **Pagamentos**: Stripe (ou Mercado Pago para BR) por assinatura; webhooks → status do plano.
- OAuth (Google/Apple) para reduzir fricção mobile.
- **LGPD**: exportação e exclusão de dados (inclui Parquet da SPEC-010), política de retenção, consentimento para uso no dataset de treino.
- Painel professor/academia (multi-aluno) — possível segundo produto; manter modelos de dados prontos para tenancy simples (FK `organization` opcional desde já).

## Eventos

Não participa do hot path. Consome `session.report.ready` (notificações futuras). Produz nada nos streams.

## Notas técnicas

- Device-id do trial: cookie httpOnly + fingerprint leve; aceitar que é burlável — é funil, não segurança.
- Quotas guardadas em Redis (contadores diários com TTL), enforcement no `POST /sessions` (SPEC-009).
