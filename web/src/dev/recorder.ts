// Instância única do gravador de fixtures. Vive fora do React de propósito: o
// loop de frames escreve nela a 15Hz e não deve provocar render nenhum.
import { createFixtureRecorder, fixtureFileName, type FixtureRecorder, type PoseFixture } from './fixtureRecorder'

function newSessionId(): string {
  const random =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID().slice(0, 8)
      : Math.random().toString(36).slice(2, 10)
  return `dev-${random}`
}

let current: FixtureRecorder = createFixtureRecorder(newSessionId())

export function getFixtureRecorder(): FixtureRecorder {
  return current
}

/** Cada gravação é uma sessão nova — `seq` recomeça do zero, como no contrato. */
export function startNewRecording(): FixtureRecorder {
  current = createFixtureRecorder(newSessionId())
  current.start()
  return current
}

export function downloadFixture(fixture: PoseFixture): void {
  const blob = new Blob([JSON.stringify(fixture, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  try {
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = fixtureFileName(fixture)
    anchor.click()
  } finally {
    URL.revokeObjectURL(url)
  }
}
