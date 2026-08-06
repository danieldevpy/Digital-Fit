#!/bin/bash

# Script para ativar plano subscriber para um usuário

set -e

EMAIL="${1:-daniel@digitalfit.com}"

echo "Ativando plano subscriber para: $EMAIL"
echo ""

docker compose exec -T api python manage.py shell << EOF
from api.models import User, Plan
from datetime import datetime, timedelta, UTC

# Busca o usuário
try:
    user = User.objects.get(email='$EMAIL')
    print(f"✓ Usuário encontrado: {user.email}")
except User.DoesNotExist:
    print(f"✗ Erro: Usuário {$EMAIL} não encontrado")
    exit(1)

# Busca o plano subscriber
try:
    plan = Plan.objects.get(slug='subscriber')
    print(f"✓ Plano encontrado: {plan.nome}")
except Plan.DoesNotExist:
    print(f"✗ Erro: Plano 'subscriber' não configurado")
    exit(1)

# Atribui o plano por 1 ano
user.plan = plan
user.plan_until = datetime.now(UTC) + timedelta(days=365)
user.save()

print(f"✓ Plano atribuído com sucesso!")
print(f"  - Plano: {user.plan.nome}")
print(f"  - Vence em: {user.plan_until.strftime('%d/%m/%Y')}")
print(f"  - Sessões/dia: {plan.daily_sessions if plan.daily_sessions > 0 else 'Ilimitadas'}")
EOF

echo ""
echo "✓ Concluído! O usuário já pode usar o app com plano subscriber."
