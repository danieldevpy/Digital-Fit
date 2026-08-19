// Página pública de um exercício (T-165, SPEC-026 §Escopo).
//
// ## Por que esta tela existe
//
// É a única parte da Fase 8 que gera tráfego de verdade. Ninguém procura "Digital Fit" —
// procuram "como fazer agachamento correto" e "squat form check app". O texto que responde a
// essas buscas já estava escrito, já era multilíngue desde a T-146, e só aparecia **depois de a
// câmera abrir**: nome, grupo muscular, dica do treinador, instrução de cena e os passos do
// guia. Esta tela é o mesmo conteúdo, servido antes de pedir qualquer permissão.
//
// ## O que ela promete a quem chega
//
// A pessoa veio com uma dúvida de execução, não com vontade de instalar coisa nenhuma. Então a
// ordem é: responder a dúvida primeiro (os passos), explicar como o produto entra (a dica de
// cena, que é o que faz a análise funcionar), e só então oferecer o treino. O CTA leva ao
// **guia daquele exercício** no app, não à home — quem clicou em "agachamento" abre agachamento.
//
// ## O que ela NÃO faz
//
// Não mostra número que ninguém mediu (SPEC-014, "honestidade > fidelidade"): não há contagem
// de quem já treinou, nota, nem tempo estimado. E não tem `HowTo` em JSON-LD — está na Fase
// Evolução da SPEC-026, para quando houver tráfego que justifique medir o ganho.
import { useT } from '../i18n'
import { appHref, siteRouteHref } from '../shell/origins'
import { IconChevronRight, IconDumbbell, IconSpark } from '../ui/icons'
import { EXERCICIOS_PUBLICOS, type ExercicioPublico } from './exercicios'
import { idDaRotaDeExercicio } from './routes'
import { SiteBar } from './SiteBar'
import { useLocale } from '../i18n'

export function ExerciseScreen({ exercicio }: { exercicio: ExercicioPublico }) {
  const t = useT()
  const locale = useLocale()
  const texto = exercicio.por_idioma[locale]

  // Os outros exercícios, para quem chegou pela busca continuar dentro do site em vez de voltar
  // para o resultado. Link interno entre páginas do mesmo assunto é o que faz um conjunto de
  // páginas valer mais que a soma delas — e é de graça, o dado já está aqui.
  const outros = EXERCICIOS_PUBLICOS.filter((outro) => outro.slug !== exercicio.slug)

  return (
    <>
      <div className="about exercicio">
        <h1 className="about__title exercicio__nome">{texto.nome}</h1>
        {texto.grupo_muscular ? (
          <p className="about__sub">
            {t('site:exercise.muscles')}: {texto.grupo_muscular}
          </p>
        ) : null}

        {exercicio.demo_img ? (
          <img className="exercicio__demo" src={exercicio.demo_img} alt={texto.nome} />
        ) : null}

        {texto.dica ? (
          <div className="feature exercicio__dica">
            <span className="feature__icon">
              <IconSpark />
            </span>
            <div>
              <p className="feature__title">{t('site:exercise.coach_tip')}</p>
              <p className="feature__text">{texto.dica}</p>
            </div>
          </div>
        ) : null}

        {texto.passos.length > 0 ? (
          <section className="exercicio__bloco">
            <h2 className="about__links-title">{t('site:exercise.how_to')}</h2>
            <ol className="exercicio__passos">
              {texto.passos.map((passo, indice) => (
                <li className="exercicio__passo" key={passo}>
                  <span className="exercicio__passo-num" aria-hidden="true">
                    {indice + 1}
                  </span>
                  <span>{passo}</span>
                </li>
              ))}
            </ol>
          </section>
        ) : null}

        <section className="exercicio__bloco">
          <h2 className="about__links-title">{t('site:exercise.scene_tip')}</h2>
          {/* Instrução de cena vazia cai na frase padrão, a mesma do app: um exercício sem
              `scene_tip` não é um exercício sem regra de enquadramento — é um que usa a de
              sempre (SPEC-015). Deixar em branco aqui esconderia justamente o que decide se a
              análise funciona. */}
          <p className="about__sub exercicio__cena">
            {texto.dica_de_cena || t('site:exercise.scene_tip_default')}
          </p>
        </section>

        <a className="v2-cta exercicio__cta" href={appHref(`#/guia/${exercicio.slug}`)}>
          <IconDumbbell className="exercicio__cta-icon" />
          {t('site:exercise.cta', { nome: texto.nome })}
        </a>
        <p className="exercicio__cta-nota">{t('site:exercise.cta_note')}</p>

        <section className="exercicio__bloco">
          <h2 className="about__links-title">{t('site:exercise.how_it_works_title')}</h2>
          <p className="about__sub exercicio__cena">{t('site:exercise.how_it_works_text')}</p>
        </section>

        {outros.length > 0 ? (
          <div className="about__links">
            <p className="about__links-title">{t('site:exercise.others')}</p>
            {outros.map((outro) => (
              <a
                key={outro.slug}
                className="about__link"
                href={siteRouteHref(idDaRotaDeExercicio(outro.slug), locale)}
              >
                {outro.por_idioma[locale].nome}
                <IconChevronRight className="about__link-icon" />
              </a>
            ))}
          </div>
        ) : null}
      </div>
      <SiteBar active={idDaRotaDeExercicio(exercicio.slug)} />
    </>
  )
}
