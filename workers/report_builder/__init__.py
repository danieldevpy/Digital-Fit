"""Consolidação da sessão em relatório (SPEC-010, T-020).

O módulo `builder` é puro: envelopes entram, um `SessionReport` sai. Quem fala com Redis e
Postgres é o comando `report_builder` do Django (`server/api/management/commands/`), porque é
lá que vive o ORM — ver ADR-008.
"""
