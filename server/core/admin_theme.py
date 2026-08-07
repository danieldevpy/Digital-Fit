"""Aparência e navegação do painel de operação (SPEC-018, T-130).

O painel é o jazzmin (AdminLTE 4 + Bootstrap 5) com a paleta da SPEC-014 por cima — a mesma
que o cliente usa, vinda dos mesmos tokens (`web/src/styles.css`). A razão não é estética: o
painel e o produto mostram os MESMOS objetos (plano, exercício, sessão), e um operador que
olha um tema claro genérico e depois o app escuro perde meio segundo a cada troca decidindo
onde está. O CSS está em `api/static/painel/digitalfit.css`; aqui ficam só as decisões que
são dado, não folha de estilo.

Três escolhas que valem explicação:

1. **`changeform_format = "single"`.** O formato de fábrica do jazzmin é `horizontal_tabs`, e
   ele é mais bonito. Mas os `fieldsets` deste projeto carregam `description` com avisos que
   mudam a operação — "cadência 0 desliga o card de calorias", "`daily_sessions = 1` no plano
   default desliga o produto para todo mundo". Aba é conteúdo escondido atrás de um clique, e
   aviso escondido é aviso que não existe.

2. **O menu lateral continua sendo gerado pelo Django.** Dava para montá-lo à mão com
   `hide_apps` + `custom_links` e ter os grupos "Suporte / Configuração / Auditoria" na
   barra. O preço seria um modelo novo registrado em `api/admin.py` que não aparece em lugar
   nenhum — e ninguém procuraria aqui. O agrupamento por caso de uso vive no dashboard
   (`server/templates/admin/index.html`), que é curadoria e pode ficar desatualizada sem
   esconder nada.

3. **As fontes vêm do mesmo CDN que o cliente usa** (`web/index.html`), pelo `@import` do CSS
   custom, e por isso o `use_google_fonts_cdn` do jazzmin fica desligado — ele traria a Source
   Sans Pro, que não é fonte deste produto. Sem rede, o fallback `system-ui` assume: é a
   mesma degradação que a SPEC-014 já aceita na landing.
"""

from __future__ import annotations

from typing import Any

#: Cada modelo com um ícone que diz o que ele é antes de o rótulo ser lido (Font Awesome 6.5
#: free, empacotado pelo jazzmin — sem CDN). `api` é a app inteira: um coração batendo, que é
#: literalmente o que este produto mede.
_ICONES = {
    "api": "fas fa-heart-pulse",
    "api.User": "fas fa-user",
    "api.Plan": "fas fa-id-card",
    "api.Exercise": "fas fa-dumbbell",
    "api.SessionResult": "fas fa-chart-line",
    "api.SessionClaim": "fas fa-fingerprint",
    "api.SiteConfig": "fas fa-sliders",
    "admin": "fas fa-shield-halved",
    "admin.LogEntry": "fas fa-clipboard-list",
}

JAZZMIN_SETTINGS: dict[str, Any] = {
    "site_title": "Digital Fit — operação",
    "site_header": "Digital Fit",
    "site_brand": "DIGITAL FIT",
    "site_logo": "painel/logo.svg",
    "login_logo": "painel/logo.svg",
    "site_icon": "painel/logo.svg",
    # O default é `img-circle`, que recortaria a marca (ela é alta e estreita, 24×28).
    "site_logo_classes": "",
    "welcome_sign": "Painel de operação",
    "copyright": "Digital Fit",
    # A busca do topo. Conta primeiro **porque suporte começa por conta**: "não consigo
    # entrar", "meu treino sumiu" e "quero assinar" se respondem todos a partir de um e-mail.
    "search_model": ["api.User", "api.Exercise"],
    # O modelo não tem campo de avatar (SPEC-011): sem esta chave o jazzmin desenha o ícone
    # genérico, que é o correto — inventar um `gravatar` mandaria o e-mail de cada operador
    # para um terceiro só para desenhar uma bolinha.
    "user_avatar": None,
    "topmenu_links": [
        {"name": "Painel", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Site", "url": "/", "new_window": True},
        {"name": "App", "url": "/app/", "new_window": True},
        {"name": "Saúde", "url": "/readyz", "new_window": True},
    ],
    "usermenu_links": [{"name": "Sair do painel", "url": "/", "icon": "fas fa-arrow-right"}],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    # Ordem do menu: o que se usa todo dia em cima (contas), o que se consulta no meio
    # (sessões), o que se muda com medo embaixo (planos, exercícios, parâmetros). A auditoria
    # fecha, porque só se procura depois que algo já aconteceu.
    "order_with_respect_to": [
        "api",
        "api.User",
        "api.SessionResult",
        "api.SessionClaim",
        "api.Plan",
        "api.Exercise",
        "api.SiteConfig",
        "admin",
        "admin.LogEntry",
    ],
    "icons": _ICONES,
    "default_icon_parents": "fas fa-circle-chevron-right",
    "default_icon_children": "fas fa-circle",
    # Abrir o formulário do relacionado numa modal poupa uma navegação em `min_plan` (o único
    # FK editável do painel). Só isso — nenhuma tela depende dele.
    "related_modal_active": True,
    "custom_css": "painel/digitalfit.css",
    "custom_js": None,
    "use_google_fonts_cdn": False,
    # O construtor de tema do jazzmin escreve `JAZZMIN_UI_TWEAKS` na tela. Ligado em produção,
    # ele oferece a todo operador um seletor de cor que não persiste em lugar nenhum.
    "show_ui_builder": False,
    "show_theme_chooser": False,
    "changeform_format": "single",
    "changeform_format_overrides": {},
    "language_chooser": False,
}

#: O tema Bootstrap fica em `default` e o esquema em `dark` de propósito: os bootswatch
#: escuros (darkly, cyborg) trazem paleta própria, e o `digitalfit.css` teria de desfazer as
#: duas. Com o `default` em modo escuro sobra só o conjunto de variáveis do Bootstrap 5.3
#: para sobrescrever — que é exatamente o que o CSS faz.
JAZZMIN_UI_TWEAKS: dict[str, Any] = {
    "theme": "default",
    "default_theme_mode": "dark",
    "navbar_small_text": False,
    "footer_small_text": True,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": False,
    "accent": "accent-primary",
    "navbar": "navbar-dark",
    "no_navbar_border": True,
    # Cabeçalho e barra lateral fixos: as listas deste painel são longas (sessões, auditoria) e
    # sem isso a navegação some depois do primeiro scroll.
    "navbar_fixed": True,
    "sidebar_fixed": True,
    "footer_fixed": False,
    "layout_boxed": False,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}
