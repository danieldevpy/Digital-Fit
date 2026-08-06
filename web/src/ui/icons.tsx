// Ícones inline (SVG). Nada de CDN ou pacote de ícones: o app precisa funcionar
// dentro do compose sem rede externa, igual aos assets do MediaPipe.
interface IconProps {
  className?: string
}

const base = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

export function IconSeries({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M7 3v3.2a3 3 0 0 0 1.2 2.4L12 12l3.8-3.4A3 3 0 0 0 17 6.2V3" />
      <path d="M7 21v-3.2a3 3 0 0 1 1.2-2.4L12 12l3.8 3.4a3 3 0 0 1 1.2 2.4V21" />
      <path d="M6 3h12M6 21h12" />
    </svg>
  )
}

export function IconPulse({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M2 12h3l2.5-7 4 14 3-9 2 2h5.5" />
    </svg>
  )
}

export function IconAngle({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M5 19h15" />
      <path d="M5 19 15 5" />
      <path d="M5 19a9 9 0 0 0 6.2-2.4" />
    </svg>
  )
}

export function IconFlame({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M12 3c.6 3 3.2 4 3.2 4S17 9 17 12a5 5 0 0 1-10 0c0-2 1.3-3.6 2.4-4.6C10.6 6.2 12 5 12 3Z" />
      <path d="M12 21a2.6 2.6 0 0 0 2.6-2.6c0-1.6-2.6-3.4-2.6-3.4s-2.6 1.8-2.6 3.4A2.6 2.6 0 0 0 12 21Z" />
    </svg>
  )
}

export function IconHome({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M4 10.5 12 4l8 6.5V19a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 19v-8.5Z" />
      <path d="M9.5 20.5V14h5v6.5" />
    </svg>
  )
}

export function IconDumbbell({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M3 9v6M6.5 6.5v11M17.5 6.5v11M21 9v6" />
      <path d="M6.5 12h11" />
    </svg>
  )
}

export function IconChart({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M5 20V11M12 20V4M19 20v-6" />
    </svg>
  )
}

export function IconUser({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <circle cx="12" cy="8" r="3.6" />
      <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
    </svg>
  )
}

/* ---------- ícones da UI v2 (SPEC-014) ---------- */

/** A figura neon da marca (braços para cima, como o hero). */
export function IconLogo({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 28" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" className={className} aria-hidden="true">
      <circle cx="12" cy="4.5" r="3" />
      <path d="M12 8v7 M5 3l4 6 M19 3l-4 6 M12 15l-5 10 M12 15l5 10" />
    </svg>
  )
}

export function IconSpark({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.4 2.4M15.6 15.6 18 18M18 6l-2.4 2.4M8.4 15.6 6 18" />
    </svg>
  )
}

export function IconTarget({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="4.5" />
      <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
    </svg>
  )
}

export function IconCounter({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <rect x="3.5" y="5" width="17" height="14" rx="2.5" />
      <path d="M8 10v4M12 9v6M16 11v2" />
    </svg>
  )
}

export function IconShieldCheck({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M12 3 5 5.6v5.2c0 4.6 3 7.7 7 9.6 4-1.9 7-5 7-9.6V5.6L12 3Z" />
      <path d="m9 12 2.2 2.2L15.4 10" />
    </svg>
  )
}

export function IconHeart({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M12 20 4 12a5.4 5.4 0 0 1 8-7.2A5.4 5.4 0 0 1 20 12l-8 8Z" />
    </svg>
  )
}

export function IconMusic({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M9 18V5l12-2v13" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="16" r="3" />
    </svg>
  )
}

export function IconPrev({ className }: IconProps) {
  return (
    <svg viewBox="0 0 16 14" className={className} aria-hidden="true">
      <path d="M3 1v12" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
      <path d="M14 1 5 7l9 6Z" fill="currentColor" />
    </svg>
  )
}

export function IconNext({ className }: IconProps) {
  return (
    <svg viewBox="0 0 16 14" className={className} aria-hidden="true">
      <path d="M13 1v12" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
      <path d="M2 1l9 6-9 6Z" fill="currentColor" />
    </svg>
  )
}

export function IconPlay({ className }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" className={className} aria-hidden="true">
      <path d="M6 3 17 10 6 17Z" fill="currentColor" />
    </svg>
  )
}

export function IconStop({ className }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" className={className} aria-hidden="true">
      <rect x="4.5" y="4.5" width="11" height="11" rx="2" fill="currentColor" />
    </svg>
  )
}

/** Primeiro degrau do CTA da pré-configuração: ligar a câmera (ver `session/startGate.ts`). */
export function IconCamera({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M3 8.5a2 2 0 0 1 2-2h2.2l1.3-2h6l1.3 2H19a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" />
      <circle cx="12" cy="12.5" r="3.4" />
    </svg>
  )
}

export function IconMirror({ className }: IconProps) {
  return (
    <svg viewBox="0 0 14 18" fill="none" stroke="currentColor" strokeWidth={1.6} className={className} aria-hidden="true">
      <rect x="1" y="1" width="12" height="16" rx="3" />
      <path d="M5 14.5h4" strokeLinecap="round" />
    </svg>
  )
}

export function IconZoom({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <circle cx="10" cy="10" r="6.5" />
      <path d="M20 20 15.5 15.5" />
      <path d="M7.5 10h5" />
    </svg>
  )
}

export function IconTimer({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M9 2h6" />
      <path d="M12 9v4l2.6 1.6" />
      <path d="m18 5.5 1.5 1.5" />
      <circle cx="12" cy="14" r="7.5" />
    </svg>
  )
}

export function IconChevronRight({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="m9 5 7 7-7 7" />
    </svg>
  )
}

/** Mini-onda decorativa dos cards de exercício (traço único, não é dado). */
export function IconWave({ className }: IconProps) {
  return (
    <svg viewBox="0 0 72 18" fill="none" className={className} aria-hidden="true">
      <path
        d="M0 10 C7 10 8 4 14 4 S22 15 29 15 S38 5 45 7 S54 12 61 9 S68 6 72 8"
        stroke="currentColor"
        strokeWidth={1.8}
      />
    </svg>
  )
}

/* ---------- figuras de exercício (T-082) ----------
 *
 * Uma pose por exercício, num vocabulário só: mesma malha `0 0 24 28`, mesmo traço 2, mesma
 * ponta redonda. Quem monta a figura de um exercício novo copia uma destas e move os pontos —
 * não inventa outro estilo de desenho. O registro que liga slug → figura, e o teste que cobra
 * a figura de todo exercício do catálogo, ficam em `exerciseFigures.ts`.
 *
 * SEPARADAS do `IconLogo` de propósito, apesar de a do polichinelo nascer idêntica a ele. O
 * `IconLogo` é a assinatura da marca (T-081) e é fixo por decisão de produto; foi justamente
 * reaproveitá-lo como ícone de exercício que fez o agachamento aparecer de braços pro alto.
 * Coladas, a primeira mudança no logotipo mudaria a pose do polichinelo — ou, pior, o medo de
 * mexer numa travaria a outra.
 *
 * O que faz a figura funcionar a 22×26px NÃO é o detalhe, é a silhueta: a 22px ninguém enxerga
 * um traço, enxerga o contorno. Por isso cada pose precisa ter proporção própria — o
 * polichinelo é um X alto, o agachamento é baixo e largo. Duas poses que ocupem a mesma
 * caixa com o mesmo formato geral são indistinguíveis no card, por mais corretas que sejam.
 */
const figura = {
  viewBox: '0 0 24 28',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
}

/** Polichinelo, no alto do salto: braços em V acima da cabeça, pernas abertas. */
export function IconExJumpingJack({ className }: IconProps) {
  return (
    <svg {...figura} className={className} aria-hidden="true">
      <circle cx="12" cy="4.5" r="3" />
      <path d="M12 8v7 M5 3l4 6 M19 3l-4 6 M12 15l-5 10 M12 15l5 10" />
    </svg>
  )
}

/**
 * Agachamento, no fundo do movimento: joelhos dobrados para fora, cabeça 2,5 unidades mais
 * baixa que a das outras figuras.
 *
 * A cabeça baixa e o afastamento dos pés não são gosto — são o que separa esta silhueta da do
 * polichinelo. Medido: 17×22 contra 14×23,5, razão largura/altura 0,77 contra 0,60. O primeiro
 * desenho desta task tinha os joelhos dobrados certos e razão 0,65, perto demais do
 * polichinelo: correto no traço e ambíguo no card, que é onde a figura vive.
 *
 * Os braços horizontais são os braços à frente em escorço — a mesma posição que o
 * `guide_steps` do agachamento descreve em texto ("braços à frente para equilibrar"). De
 * frente, braço apontado para a câmera não tem comprimento na tela; desenhá-lo "correto"
 * daria dois cotocos sobre o peito, ilegíveis. O traço lateral é a convenção que lê.
 */
export function IconExSquat({ className }: IconProps) {
  return (
    <svg {...figura} className={className} aria-hidden="true">
      <circle cx="12" cy="7" r="3" />
      <path d="M12 10.5v4.5 M3.5 13.5H9 M20.5 13.5H15 M12 15l-6 4.5 1.5 6.5 M12 15l6 4.5-1.5 6.5" />
    </svg>
  )
}

/**
 * Flexão, no fundo do movimento: corpo deitado de perfil, cotovelo dobrado para trás.
 *
 * As duas figuras de chão (esta e a do abdominal) são as primeiras DEITADAS do vocabulário, e
 * é isso que as separa de tudo que já existia: as três de pé são verticais e altas, estas duas
 * são largas e baixas. No card, a diferença de silhueta chega antes do desenho.
 *
 * Entre si, elas se separam pelo que sustenta o corpo: aqui é o braço até o chão, com o resto
 * do corpo suspenso numa linha; no abdominal é o joelho dobrado para cima. Desenhar a flexão
 * na prancha (braço reto) as deixaria parecidas demais — o cotovelo dobrado é o que diz "isto
 * é uma flexão" e não "isto é uma pessoa deitada".
 */
export function IconExPushUp({ className }: IconProps) {
  return (
    <svg {...figura} className={className} aria-hidden="true">
      <circle cx="4.2" cy="17.2" r="2.8" />
      <path d="M7.2 18.8 14 21 20.8 23.4 M20.8 23.4 22.3 25.6 M7.6 19 10.8 22.2 7.4 25.4" />
    </svg>
  )
}

/**
 * Abdominal, no topo do movimento: costas no chão, tronco encolhido, joelho dobrado para cima.
 *
 * O joelho alto não é enfeite de desenho — é a montagem que o exercício exige para ser medido
 * (é dele que sai a referência da contagem, ver `abdominal.py`). A figura afirma a mesma coisa
 * que o Guia pede em texto.
 */
export function IconExCrunch({ className }: IconProps) {
  return (
    <svg {...figura} className={className} aria-hidden="true">
      <circle cx="3.8" cy="19.4" r="2.8" />
      <path d="M6.6 20.8 13 24 M13 24 17.6 18.6 21.6 24.6 M7 21.4 10 23.2" />
    </svg>
  )
}

/**
 * Em pé, neutra — a figura de quem ainda não tem figura.
 *
 * Existe para o fallback do registro não poder ser o polichinelo: um exercício novo sem pose
 * própria mostraria "um polichinelo" no card, que é uma afirmação errada sobre o que a pessoa
 * vai fazer. Esta não afirma nada além de "uma pessoa" — e, sendo visivelmente sem graça,
 * denuncia a figura faltando em vez de esconder.
 */
export function IconExStanding({ className }: IconProps) {
  return (
    <svg {...figura} className={className} aria-hidden="true">
      <circle cx="12" cy="4.5" r="3" />
      <path d="M12 8v7 M9 9l-1 8 M15 9l1 8 M12 15l-3 10 M12 15l3 10" />
    </svg>
  )
}
