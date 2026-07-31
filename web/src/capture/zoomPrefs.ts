// Preferência de zoom da câmera. Mesma casa das outras preferências de conforto
// (session/configPrefs.ts): não é meta do servidor, só lembra o que funcionou para esta
// pessoa da última vez — quem já achou a distância certa não quer reajustar toda sessão.
const ZOOM_KEY = 'digitalfit.zoom'

/** Neutro: câmera sem zoom nenhum aplicado. */
export const ZOOM_DEFAULT = 1

function clamp(value: unknown, min: number, max: number, fallback: number): number {
  const n = Number(value)
  if (!Number.isFinite(n)) return fallback
  return Math.max(min, Math.min(max, n))
}

/** Lida em bruto: quem usa (`useCamera.ts`) recorta para a faixa que o hardware aceita. */
export function zoomPreference(): number {
  try {
    const raw = window.localStorage.getItem(ZOOM_KEY)
    if (raw === null) return ZOOM_DEFAULT
    return clamp(raw, 0.1, ZOOM_DEFAULT, ZOOM_DEFAULT)
  } catch {
    return ZOOM_DEFAULT
  }
}

export function setZoomPreference(value: number): number {
  try {
    window.localStorage.setItem(ZOOM_KEY, String(value))
  } catch {
    // Sem armazenamento (Safari privado): vale pela sessão atual e pronto.
  }
  return value
}
