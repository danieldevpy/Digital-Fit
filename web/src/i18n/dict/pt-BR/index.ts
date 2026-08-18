// Agrega os nove namespaces num objeto só, para o runtime (`i18n/index.ts`) ter um ponto de
// import estável. Tarefas da Onda 2 não tocam este arquivo — só o `export const <namespace>`
// dentro do próprio arquivo delas — então ele não é o `pt-BR.json` único que o plano evitou
// (PLANO-I18N.md §3.2): a lista de nomes já existe desde a T-142, cada um ainda vazio.
import { account } from './account'
import { catalog } from './catalog'
import { errors } from './errors'
import { funnel } from './funnel'
import { progress } from './progress'
import { report } from './report'
import { session } from './session'
import { shell } from './shell'
import { site } from './site'

export const dict = { account, catalog, errors, funnel, progress, report, session, shell, site }
