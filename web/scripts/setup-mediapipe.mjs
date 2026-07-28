// Prepara os assets locais do MediaPipe (SPEC-005): runtime WASM + modelo.
// Rodado por `npm run setup` (e automaticamente antes de `dev`/`build`).
// Nada disso é versionado — ver web/.gitignore.
import { cp, mkdir, stat, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')

const WASM_SRC = resolve(webRoot, 'node_modules/@mediapipe/tasks-vision/wasm')
const WASM_DEST = resolve(webRoot, 'public/wasm')

// Modelo `lite` — mesma config usada pelo probe (SPEC-001) e pela sessão real.
const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task'
const MODEL_DEST = resolve(webRoot, 'public/models/pose_landmarker_lite.task')

async function exists(path) {
  try {
    await stat(path)
    return true
  } catch {
    return false
  }
}

async function copyWasm() {
  if (!(await exists(WASM_SRC))) {
    throw new Error(`WASM do tasks-vision não encontrado em ${WASM_SRC}. Rode "npm install" antes.`)
  }
  await cp(WASM_SRC, WASM_DEST, { recursive: true })
  console.log(`[setup] wasm  → public/wasm`)
}

async function downloadModel() {
  if (await exists(MODEL_DEST)) {
    console.log('[setup] modelo → já presente, pulando download')
    return
  }
  await mkdir(dirname(MODEL_DEST), { recursive: true })
  const response = await fetch(MODEL_URL)
  if (!response.ok) {
    throw new Error(`Falha ao baixar o modelo (${response.status} ${response.statusText})`)
  }
  await writeFile(MODEL_DEST, Buffer.from(await response.arrayBuffer()))
  console.log('[setup] modelo → public/models/pose_landmarker_lite.task')
}

await copyWasm()
await downloadModel()
