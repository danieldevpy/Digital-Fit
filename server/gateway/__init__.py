"""Gateway WebSocket (Django Channels) — SPEC-002.

Fica dentro do projeto Django por simplicidade (ADR-002), mas conversa com o resto **somente
por eventos**: recebe do cliente e publica no stream; assina `events.analysis` e empurra ao
cliente. Nenhum import de worker além do contrato e do barramento compartilhado.
"""
