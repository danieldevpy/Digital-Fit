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

// Onde procurar o modelo antes de sair para a rede. Mesma ideia do `resolve_model_path` do
// Python (eval/sources.py): o arquivo já costuma existir na máquina, e no container do compose
// ele chega por bind mount — a primeira subida não pode depender de internet.
const MODEL_LOCAL_SOURCES = [
  process.env.DIGITALFIT_POSE_MODEL,
  resolve(webRoot, '../eval/models/pose_landmarker_lite.task'),
  '/models/pose_landmarker_lite.task',
].filter(Boolean)

async function downloadModel() {
  if (await exists(MODEL_DEST)) {
    console.log('[setup] modelo → já presente, pulando download')
    return
  }
  await mkdir(dirname(MODEL_DEST), { recursive: true })

  for (const origem of MODEL_LOCAL_SOURCES) {
    if (await exists(origem)) {
      await cp(origem, MODEL_DEST)
      console.log(`[setup] modelo → copiado de ${origem}`)
      return
    }
  }

  const response = await fetch(MODEL_URL)
  if (!response.ok) {
    throw new Error(`Falha ao baixar o modelo (${response.status} ${response.statusText})`)
  }
  await writeFile(MODEL_DEST, Buffer.from(await response.arrayBuffer()))
  console.log('[setup] modelo → public/models/pose_landmarker_lite.task')
}

await copyWasm()
await downloadModel()
