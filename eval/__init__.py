"""Bancada de avaliação (`evalctl`) — SPEC-012.

Roda o pipeline real (normalização + FSM dos workers) sobre **arquivos de vídeo**, sem
sistema no ar e sem Docker: é o que transforma "melhorar a contagem" em medição, e não em
impressão.

Nível 1 da pirâmide (fixtures de keypoints) vive no `pytest`; nível 2 (vídeo) é este pacote;
nível 3 (câmera ao vivo) é o cliente web.

Dependências pesadas (MediaPipe, OpenCV) ficam no extra `eval` e são importadas **tarde**, só
quando um vídeo de verdade precisa ser lido — `import eval.pipeline` não puxa nada disso.
"""
