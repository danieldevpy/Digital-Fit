"""Como cada tabela se chama na tela do painel (SPEC-018, T-130).

`AlterModelOptions` **não toca no banco**: nenhuma coluna, nenhum índice, nenhum dado. É uma
migration de estado, e existe só porque o Django guarda `verbose_name` no histórico de
migrations junto com o resto do `Meta`. Rodá-la em produção é instantâneo e reversível.

Por que os nomes: sem `verbose_name` o Django deriva o rótulo do nome da CLASSE, e com
`USE_I18N = False` (settings) ele nem passa por tradução. O operador via "Session claims" e
"Session results" — dois nomes que vêm do vocabulário do event bus, não do vocabulário de quem
atende o suporte. "Treinos realizados" e "Donos de sessão" dizem o que a tabela responde.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_cadencia_de_referencia'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='exercise',
            options={'ordering': ['ordem', 'slug'], 'verbose_name': 'exercício', 'verbose_name_plural': 'exercícios'},
        ),
        migrations.AlterModelOptions(
            name='exerciseguidestep',
            options={'ordering': ['ordem', 'pk'], 'verbose_name': 'passo do guia', 'verbose_name_plural': 'passos do guia'},
        ),
        migrations.AlterModelOptions(
            name='plan',
            options={'ordering': ['ordem', 'slug'], 'verbose_name': 'plano', 'verbose_name_plural': 'planos'},
        ),
        migrations.AlterModelOptions(
            name='sessionclaim',
            options={'ordering': ['-created_at'], 'verbose_name': 'dono de sessão', 'verbose_name_plural': 'donos de sessão'},
        ),
        migrations.AlterModelOptions(
            name='sessionresult',
            options={'ordering': ['-created_at'], 'verbose_name': 'treino realizado', 'verbose_name_plural': 'treinos realizados'},
        ),
        migrations.AlterModelOptions(
            name='user',
            options={'verbose_name': 'conta', 'verbose_name_plural': 'contas'},
        ),
    ]
