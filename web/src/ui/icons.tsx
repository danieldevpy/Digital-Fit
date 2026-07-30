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

export function IconMirror({ className }: IconProps) {
  return (
    <svg viewBox="0 0 14 18" fill="none" stroke="currentColor" strokeWidth={1.6} className={className} aria-hidden="true">
      <rect x="1" y="1" width="12" height="16" rx="3" />
      <path d="M5 14.5h4" strokeLinecap="round" />
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
