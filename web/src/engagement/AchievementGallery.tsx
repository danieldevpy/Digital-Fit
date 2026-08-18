// A galeria de conquistas (SPEC-019 §Superfícies / T-089).
//
// Bloqueadas aparecem **apagadas, com nome e descrição legíveis** — e isso é a escolha da
// spec, não um detalhe de CSS. Uma vitrine que escondesse o que falta seria um troféu; uma que
// mostra transforma a tela num objetivo, que é a razão de a mecânica existir.
import { useT } from '../i18n'
import type { Achievement } from './api'

const ICONE: Record<string, string> = {
  'primeira-sessao': '🎬',
  'fogo-7': '🔥',
  'semana-cheia': '📅',
  centena: '💯',
  'sem-reparo': '✨',
  'fogo-30': '🏆',
  milheiro: '🚀',
}

/** Slug sem ícone não quebra a tela: o catálogo é do servidor e pode crescer sem deploy do web. */
const ICONE_PADRAO = '🎖️'

export function AchievementGallery({ lista }: { lista: Achievement[] }) {
  const t = useT()

  if (lista.length === 0) return null

  const ganhas = lista.filter((c) => c.earned).length

  return (
    <div className="eng__ach">
      <p className="v2-label">
        {t('account:ach.title')} <span className="num tabular">{ganhas}</span>/
        <span className="num tabular">{lista.length}</span>
      </p>
      <ul className="eng__ach-grid">
        {lista.map((conquista) => (
          <li
            key={conquista.slug}
            className={`eng__ach-item ${conquista.earned ? 'eng__ach-item--on' : ''}`}
            title={conquista.description}
          >
            <span className="eng__ach-icon" aria-hidden="true">
              {ICONE[conquista.slug] ?? ICONE_PADRAO}
            </span>
            <span className="eng__ach-name">{conquista.name}</span>
            <span className="eng__ach-desc">{conquista.description}</span>
            {/* O estado vai em palavras para quem usa leitor de tela: o cinza não é lido. */}
            <span className="sr-only">
              {conquista.earned ? t('account:ach.earned') : t('account:ach.locked')}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
