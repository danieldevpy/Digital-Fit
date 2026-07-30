// Prepara os assets locais do MediaPipe (SPEC-005): runtime WASM + modelo.
// Rodado por `npm run setup` (e automaticamente antes de `dev`/`build`).
// Nada disso é versionado — ver web/.gitignore.
import { cp, mkdir, readdir, stat, writeFile } from 'node:fs/promises'
import { basename, dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')

const WASM_SRC = resolve(webRoot, 'node_modules/@mediapipe/tasks-vision/wasm')
const WASM_DEST = resolve(webRoot, 'public/wasm')

// Tamanhos DESCOMPRIMIDOS dos assets, por nome de arquivo (T-071).
//
// Existe porque não há como o cliente descobrir isso do servidor: sob gzip o nginx responde sem
// `Content-Length` (nem no GET, nem no HEAD — verificado), e o `fetch` não deixa pedir `identity`
// (`Accept-Encoding` é cabeçalho proibido no browser). Sem esse número o download de 17 MB não
// tem porcentagem, só "3,4 MB baixados" — e quem espera não sabe se falta um terço ou o dobro.
//
// O tamanho vale para o stream JÁ DESCOMPRIMIDO, que é exatamente o que o cliente conta ao ler o
// corpo. É por isso que o número certo é o do arquivo no disco, e não o da rede.
const MANIFEST_DEST = resolve(webRoot, 'public/pose-assets.json')

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

/** Manifesto de tamanhos: lido pelo cliente para a barra de progresso ter denominador. */
async function writeManifest() {
  const sizes = {}

  for (const nome of await readdir(WASM_DEST)) {
    // Só os binários interessam: o cliente aquece o `.wasm` que o FilesetResolver escolher, e
    // os `.js` de cola são pequenos e não valem linha no manifesto.
    if (!nome.endsWith('.wasm')) continue
    sizes[nome] = (await stat(resolve(WASM_DEST, nome))).size
  }
  sizes[basename(MODEL_DEST)] = (await stat(MODEL_DEST)).size

  await writeFile(MANIFEST_DEST, `${JSON.stringify(sizes, null, 2)}\n`)
  console.log(`[setup] manifesto → public/pose-assets.json (${Object.keys(sizes).length} arquivos)`)
}

await copyWasm()
await downloadModel()
await writeManifest()
