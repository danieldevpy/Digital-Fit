"""Testes da FSM da flexão (T-106 / SPEC-007 / SPEC-020 Tier C).

Mesmos critérios de aceite dos outros exercícios, sobre o mesmo pipeline real: gerador
sintético → `normalize()` → FSM. O que se testa é a contagem que o worker vai produzir.

Dois blocos que só existem aqui, e que são a razão de o módulo ter sido escrito como foi:

- **Invariância ao formato do quadro.** Um corpo deitado é medido no eixo horizontal e se move
  no vertical, e o espaço normalizado do MediaPipe não é isotrópico (`x` divide pela largura,
  `y` pela altura). Um limiar "em torsos" herdaria o formato do vídeo. Os testes esticam o
  quadro de propósito.
- **A referência é a prancha da própria pessoa.** É o que faz o limiar não depender das
  proporções do boneco do gerador — o erro medido em `[A/T-106]`, que deixou o limiar do
  agachamento inalcançável para gente real.
"""

import pytest

from tests.synthetic_keypoints import (
    ELBOW_BOTTOM,
    ELBOW_TOP,
    HIPS_PIKED,
    HIPS_SAGGED,
    Pose,
    PushUpPose,
    jumping_jack_poses,
    plank_pose,
    pushup_poses,
    sequence,
    session_poses,
    squat_poses,
    still_poses,
)
from workers.analysis_worker.exercises import (
    EXERCISES,
    PushUpAnalyzer,
    PushUpThresholds,
    feed,
    get_analyzer,
)
from workers.shared.events import Code, ExercisePhase, Phase, QualitySignal, RepDetected
from workers.shared.normalize import NormFrame, normalize


def analisar(frames, analyzer: PushUpAnalyzer | None = None) -> tuple:
    analyzer = analyzer or PushUpAnalyzer()
    eventos = []
    for frame in normalize(frames):
        eventos.extend(feed(analyzer, frame))
    return analyzer, eventos


def do_tipo(eventos, tipo) -> list:
    return [evento for evento in eventos if isinstance(evento, tipo)]


def codigos(eventos) -> set[str]:
    return {evento.code.value for evento in do_tipo(eventos, QualitySignal)}


def um_frame(pose: PushUpPose, **kwargs) -> NormFrame:
    return normalize(sequence([pose], **kwargs))[0]


# --------------------------------------------------------------------------------------
# Critério 1 — flexões limpas contam exatamente
# --------------------------------------------------------------------------------------


def test_vinte_flexoes_limpas_contam_exatamente_vinte() -> None:
    analyzer, eventos = analisar(sequence(pushup_poses(20)))

    assert analyzer.rep_count == 20
    assert [evento.rep_count for evento in do_tipo(eventos, RepDetected)] == list(range(1, 21))


@pytest.mark.parametrize("reps", [1, 5, 20])
def test_contagem_bate_para_diferentes_quantidades(reps: int) -> None:
    analyzer, _ = analisar(sequence(pushup_poses(reps)))

    assert analyzer.rep_count == reps


@pytest.mark.parametrize("fps", [10.0, 15.0, 30.0])
def test_contagem_independe_do_fps(fps: float) -> None:
    poses = pushup_poses(10, frames_per_rep=max(int(fps), 8))

    analyzer, _ = analisar(sequence(poses, fps=fps))

    assert analyzer.rep_count == 10


@pytest.mark.parametrize("torso", [0.15, 0.30, 0.45])
def test_contagem_independe_da_distancia_da_camera(torso: float) -> None:
    analyzer, _ = analisar(sequence(pushup_poses(8), torso=torso))

    assert analyzer.rep_count == 8


def test_emite_fase_a_cada_transicao() -> None:
    _, eventos = analisar(sequence(pushup_poses(3)))

    fases = [evento.phase for evento in do_tipo(eventos, ExercisePhase)]

    assert fases == [Phase.PEAK, Phase.REST] * 3


def test_flexao_limpa_nao_gera_critica_de_execucao() -> None:
    _, eventos = analisar(sequence(pushup_poses(10)))

    assert do_tipo(eventos, QualitySignal) == []


def test_sessao_com_countdown_na_prancha_conta_tudo() -> None:
    """A sessão real começa parada — e, na flexão, parada JÁ é a prancha.

    É o caminho que o worker percorre desde a T-019: o countdown mede o corpo e só então a
    FSM vê os frames. Aqui ele também é o que estabelece a referência da prancha.
    """
    poses = session_poses(pushup_poses(8), still=plank_pose())

    analyzer, _ = analisar(sequence(poses))

    assert analyzer.rep_count == 8


# --------------------------------------------------------------------------------------
# Critério 2 — rep rasa não conta e gera o sinal certo
# --------------------------------------------------------------------------------------


def test_flexao_rasa_nao_conta_e_avisa() -> None:
    """Desceu, mas o cotovelo parou em ~110°–127°: não é flexão, é meia flexão."""
    analyzer, eventos = analisar(sequence(pushup_poses(3, amplitude=0.75)))

    assert analyzer.rep_count == 0
    assert codigos(eventos) == {Code.PUSHUP_TOO_SHALLOW.value}
    assert len(do_tipo(eventos, QualitySignal)) == 3  # um por tentativa, não um por frame


def test_sinal_carrega_a_profundidade_medida_e_o_indice() -> None:
    _, eventos = analisar(sequence(pushup_poses(1, amplitude=0.75)))

    sinal = next(e for e in do_tipo(eventos, QualitySignal) if e.code is Code.PUSHUP_TOO_SHALLOW)
    limiares = PushUpThresholds()

    assert limiares.down_depth <= sinal.value <= limiares.shallow_depth
    assert sinal.rep_index == 1


def test_movimento_minusculo_nao_gera_nem_rep_nem_sinal() -> None:
    """Abaixo da faixa "quase desceu" não há o que criticar — não é tentativa.

    Medido: com amplitude 0,6 o cotovelo chega a ~123° e o One Euro ainda corta o fundo, então
    a profundidade fica em 0,911 — acima da faixa de crítica (0,82–0,90). É o mesmo silêncio
    que o polichinelo guarda para quem mal levanta o braço.
    """
    analyzer, eventos = analisar(sequence(pushup_poses(3, amplitude=0.6)))

    assert analyzer.rep_count == 0
    assert do_tipo(eventos, QualitySignal) == []


def test_rep_valida_depois_de_rasa_conta_normalmente() -> None:
    poses = pushup_poses(2, amplitude=0.75) + pushup_poses(3)

    analyzer, eventos = analisar(sequence(poses))

    assert analyzer.rep_count == 3
    assert Code.PUSHUP_TOO_SHALLOW.value in codigos(eventos)


# --------------------------------------------------------------------------------------
# Critério 3 — nada de falso positivo com pessoa parada
# --------------------------------------------------------------------------------------


def test_pessoa_na_prancha_com_tremor_nao_conta_nada() -> None:
    frames = sequence([plank_pose()] * 300, jitter=0.006, seed=13)

    analyzer, eventos = analisar(frames)

    assert analyzer.rep_count == 0
    assert do_tipo(eventos, RepDetected) == []


def test_pessoa_parada_embaixo_nao_conta_nada() -> None:
    """Segurar o fundo da flexão não é repetir — a rep nasce na SUBIDA."""
    fundo = PushUpPose(elbow_angle=ELBOW_BOTTOM)

    analyzer, _ = analisar(sequence([fundo] * 200, jitter=0.006, seed=17))

    assert analyzer.rep_count == 0


def test_oscilar_no_limiar_nao_conta_duas_vezes() -> None:
    """Histerese: ficar na fronteira da descida não pode virar contagem."""
    limiares = PushUpThresholds()
    fronteira = [
        PushUpPose(elbow_angle=112.0),
        PushUpPose(elbow_angle=104.0),
    ] * 40

    analyzer, _ = analisar(sequence([plank_pose(), *fronteira]))

    assert limiares.down_depth < limiares.up_depth  # a folga existe
    assert analyzer.rep_count == 0


def test_debounce_ignora_transicao_mais_rapida_que_250ms() -> None:
    """A 60 fps, descer e subir em 4 frames (66 ms) é ruído, não repetição."""
    analyzer, _ = analisar(sequence(pushup_poses(6, frames_per_rep=4), fps=60.0))

    assert analyzer.rep_count == 0


def test_frames_degradados_congelam_a_fsm() -> None:
    analyzer, _ = analisar(sequence(pushup_poses(5), visibility=0.1))

    assert analyzer.rep_count == 0
    assert analyzer.summary()["frames_degraded"] > 0


# --------------------------------------------------------------------------------------
# Critério 4 — postura do corpo vira crítica JUNTO com a repetição
# --------------------------------------------------------------------------------------


def test_quadril_caindo_conta_a_rep_e_critica() -> None:
    """Quadril caído é uma flexão que aconteceu e foi mal feita — conta e reclama.

    É a diferença deliberada para a rep rasa, que é uma flexão que NÃO aconteceu.
    """
    analyzer, eventos = analisar(sequence(pushup_poses(5, hip_offset=HIPS_SAGGED)))

    assert analyzer.rep_count == 5
    assert codigos(eventos) == {Code.HIPS_SAGGING.value}
    assert len(do_tipo(eventos, QualitySignal)) == 5  # um por repetição


def test_quadril_empinado_tem_codigo_proprio() -> None:
    """Dois códigos e não um com sinal: o conserto é oposto."""
    analyzer, eventos = analisar(sequence(pushup_poses(5, hip_offset=HIPS_PIKED)))

    assert analyzer.rep_count == 5
    assert codigos(eventos) == {Code.HIPS_PIKED.value}


def test_corpo_alinhado_nao_gera_critica_de_quadril() -> None:
    _, eventos = analisar(sequence(pushup_poses(6)))

    assert codigos(eventos) & {Code.HIPS_SAGGING.value, Code.HIPS_PIKED.value} == set()


def test_desvio_pequeno_de_quadril_nao_reclama() -> None:
    """Ninguém faz flexão com o corpo numa régua. A tolerância existe para isso."""
    _, eventos = analisar(sequence(pushup_poses(5, hip_offset=0.08)))

    assert codigos(eventos) == set()


# --------------------------------------------------------------------------------------
# Critério 5 — o porteiro de postura (regressão do bug relatado em produção)
# --------------------------------------------------------------------------------------
#
# Relato de quem testou: "dependendo da posição ele já contava, quando levantava ele contava".
# A causa: a altura do ombro sobre o pulso de quem está EM PÉ com os braços baixos é +0,73
# torsos — quase idêntica à de uma prancha. Levantar e baixar os braços era, para a FSM,
# descer e subir uma flexão. Estes testes reproduzem o relato e não deixam voltar.


def test_pessoa_em_pe_levantando_os_bracos_nao_conta_flexao() -> None:
    """O bug, exatamente como foi relatado. Antes do porteiro: 10 reps."""
    analyzer, eventos = analisar(sequence(jumping_jack_poses(10)))

    assert analyzer.rep_count == 0
    assert do_tipo(eventos, RepDetected) == []


def test_pessoa_em_pe_parada_nao_conta_flexao() -> None:
    analyzer, _ = analisar(sequence(still_poses(120)))

    assert analyzer.rep_count == 0
    assert analyzer.summary()["frames_off_posture"] == 120


def test_agachar_na_frente_da_camera_nao_conta_flexao() -> None:
    analyzer, _ = analisar(sequence(squat_poses(10)))

    assert analyzer.rep_count == 0


def test_o_caminho_real_conta_exatamente_as_flexoes() -> None:
    """Chega em pé, deita, treina, levanta — que é como toda sessão de verdade acontece.

    O teste que amarra as duas pontas: o porteiro tem de recusar as duas partes em pé E deixar
    a contagem do meio intacta. Um porteiro que só soubesse recusar passaria no teste anterior
    e quebraria o produto.
    """
    poses = [*still_poses(30), *pushup_poses(6), *still_poses(30)]

    analyzer, _ = analisar(sequence(poses))

    assert analyzer.rep_count == 6
    assert analyzer.summary()["frames_off_posture"] > 0


def test_em_pe_nao_contamina_a_referencia_da_prancha() -> None:
    """A referência só cresce com o porteiro aberto — senão o em pé fixa a prancha errada.

    Sem esta regra, os frames em pé (altura 0,73) e os de prancha (1,15) entrariam na mesma
    referência, e a profundidade de cada flexão passaria a ser medida contra um corpo que
    ninguém fez.
    """
    so_flexao, _ = analisar(sequence(pushup_poses(6)))
    depois_de_ficar_em_pe, _ = analisar(sequence([*still_poses(40), *pushup_poses(6)]))

    assert depois_de_ficar_em_pe.rep_count == so_flexao.rep_count == 6


def test_flexao_de_joelhos_conta():
    """A progressão com que quase todo mundo começa não pode ser recusada pelo porteiro.

    É o motivo de o "chão" ser o ponto mais baixo da PERNA (joelho ou tornozelo, o que estiver
    mais embaixo) e não o tornozelo: de joelhos, o pé fica no ar, atrás.
    """
    analyzer, _ = analisar(sequence(pushup_poses(10, on_knees=True)))

    assert analyzer.rep_count == 10
    assert analyzer.summary()["frames_off_posture"] == 0


def test_o_porteiro_separa_deitado_de_em_pe_com_ordem_de_grandeza() -> None:
    """Os números que justificam os dois limiares, travados.

    A folga é o que faz o porteiro sobreviver a ruído e a câmera torta: não é uma decisão
    apertada entre 1,1 e 1,3, é 0,0 contra 2,5.
    """
    analyzer = PushUpAnalyzer()
    limiares = PushUpThresholds()

    prancha = analyzer.features(um_frame(plank_pose()))
    em_pe = PushUpAnalyzer().features(normalize(sequence([Pose()]))[0])

    assert prancha["on_floor"] is True
    assert float(prancha["trunk_spread"]) > limiares.min_trunk_spread * 2
    assert float(prancha["hands_to_ground"]) < limiares.max_hands_to_ground / 2

    assert em_pe["on_floor"] is False
    assert float(em_pe["trunk_spread"]) < 0.2
    assert float(em_pe["hands_to_ground"]) > 1.0


def test_um_frame_errado_do_modelo_nao_estraga_a_referencia() -> None:
    """A referência exige dois frames seguidos, e é por isso.

    Um único frame em que o modelo joga o ombro para longe inflaria a prancha para sempre — e
    a partir dali nenhuma flexão de verdade voltaria a marcar profundidade 1,0.
    """
    analyzer = PushUpAnalyzer()
    for frame in normalize(sequence(pushup_poses(2))):
        feed(analyzer, frame)
    referencia = analyzer._plank_height

    # Um frame solto com o corpo "esticado" 40% além do que a pessoa consegue.
    esticado = normalize(sequence([plank_pose()], torso=0.42))[0]
    analyzer.features(esticado)

    assert analyzer._plank_height == pytest.approx(referencia, rel=0.01)


# --------------------------------------------------------------------------------------
# A decisão que define o módulo: razão sobre a PRÓPRIA prancha, não constante em torsos
# --------------------------------------------------------------------------------------


def test_profundidade_e_razao_e_bate_com_a_tabela_do_docstring() -> None:
    """Os números da tabela do módulo, travados."""
    analyzer = PushUpAnalyzer()

    def profundidade(cotovelo: float) -> float:
        # A referência da prancha precisa existir antes: é ela que a razão usa.
        analyzer.features(um_frame(plank_pose()))
        return float(analyzer.features(um_frame(PushUpPose(elbow_angle=cotovelo)))["depth"])

    assert profundidade(ELBOW_TOP) == pytest.approx(1.000, abs=0.01)
    assert profundidade(130.0) == pytest.approx(0.909, abs=0.01)
    assert profundidade(115.0) == pytest.approx(0.846, abs=0.01)
    assert profundidade(ELBOW_BOTTOM) == pytest.approx(0.709, abs=0.01)
    # Monotônica: mais dobrado é sempre mais fundo, sem inversão no meio da faixa.
    valores = [profundidade(c) for c in (ELBOW_TOP, 145.0, 130.0, 115.0, ELBOW_BOTTOM)]
    assert valores == sorted(valores, reverse=True)


def test_a_contagem_nao_muda_com_o_formato_do_quadro() -> None:
    """O teste que existe por causa da anisotropia medida no corpus.

    O MediaPipe normaliza `x` pela largura e `y` pela altura, então esticar o quadro muda a
    razão entre uma medida horizontal e uma vertical — e num corpo DEITADO o torso é
    horizontal e o movimento é vertical. `sequence(torso=...)` estica exatamente esse eixo.

    Uma FSM com limiar "em torsos" quebraria aqui; a razão sobre a própria prancha não.
    """
    contagens = {
        torso: analisar(sequence(pushup_poses(10), torso=torso))[0].rep_count
        for torso in (0.12, 0.20, 0.30, 0.42)
    }

    assert set(contagens.values()) == {10}, contagens


def test_profundidade_nao_muda_com_a_posicao_no_quadro() -> None:
    """Invariância que a normalização promete e da qual a contagem depende."""
    analyzer = PushUpAnalyzer()
    analyzer.features(um_frame(plank_pose()))
    fundo = PushUpPose(elbow_angle=ELBOW_BOTTOM)

    canto = analyzer.features(um_frame(fundo, center=(0.30, 0.35)))
    meio = analyzer.features(um_frame(fundo, center=(0.5, 0.55)))

    assert float(canto["depth"]) == pytest.approx(float(meio["depth"]), abs=0.01)


def test_sem_referencia_de_prancha_a_fsm_fica_em_repouso() -> None:
    """Corpo que não está em prancha nenhuma não pode produzir profundidade.

    Sem esta trava, dividir por uma referência minúscula transformaria ruído em repetição.
    """
    analyzer = PushUpAnalyzer()
    # Um "corpo" achatado: a altura do ombro sobre a mão fica abaixo do mínimo exigido.
    feats = analyzer.features(um_frame(PushUpPose(elbow_angle=8.0)))

    assert float(feats["depth"]) == 1.0
    assert analyzer.initial_phase(feats) is Phase.REST
    assert analyzer.ready_pose(feats) is False


def test_prancha_e_a_posicao_inicial() -> None:
    analyzer = PushUpAnalyzer()
    feats_prancha = analyzer.features(um_frame(plank_pose()))

    assert analyzer.ready_pose(feats_prancha) is True

    feats_fundo = analyzer.features(um_frame(PushUpPose(elbow_angle=ELBOW_BOTTOM)))
    assert analyzer.ready_pose(feats_fundo) is False


def test_quadril_fora_da_linha_nao_e_posicao_inicial() -> None:
    """Prancha torta não é prancha — o gate de prontidão sabe disso."""
    analyzer = PushUpAnalyzer()
    feats = analyzer.features(um_frame(plank_pose(hip_offset=HIPS_SAGGED)))

    assert analyzer.ready_pose(feats) is False


# --------------------------------------------------------------------------------------
# Registro e contrato
# --------------------------------------------------------------------------------------


def test_flexao_esta_registrada_no_catalogo_do_servidor() -> None:
    assert EXERCISES["flexao"] is PushUpAnalyzer
    assert isinstance(get_analyzer("flexao"), PushUpAnalyzer)


def test_summary_traz_o_consolidado_da_sessao() -> None:
    analyzer, _ = analisar(sequence(pushup_poses(5)))

    resumo = analyzer.summary()

    assert resumo["exercise"] == "flexao"
    assert resumo["reps"] == 5
    assert resumo["cadence_rpm"] > 0
