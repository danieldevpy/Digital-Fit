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
