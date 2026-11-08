from django.db import models

from apps.donos.models import Cliente, PertenceADono
from apps.fluxos.models import Predefinicao
from apps.plataformas.models import ConexaoPlataforma


class Projeto(PertenceADono):
    """Um repositório que a central gerencia, com a predefinição de fluxo que ele segue."""

    nome = models.CharField(max_length=120)
    # PROTECT: apagar a conexão não pode apagar os projetos em silêncio.
    conexao = models.ForeignKey(ConexaoPlataforma, on_delete=models.PROTECT, related_name="+")
    repositorio_caminho = models.CharField(max_length=300)
    repositorio_id_externo = models.CharField(max_length=100)
    repositorio_url = models.CharField(max_length=500)
    cliente = models.ForeignKey(
        Cliente, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # PROTECT: apagar uma predefinição em uso não pode soltar os projetos em silêncio.
    predefinicao = models.ForeignKey(
        Predefinicao, null=True, blank=True, on_delete=models.PROTECT, related_name="projetos"
    )
    ativo = models.BooleanField(default=True)
    ultima_conferencia = models.JSONField(default=list, blank=True)
    ultima_conferencia_em = models.DateTimeField(null=True, blank=True)

    # Não vai para o banco: a mensagem do último «preparar» que falhou, só para a resposta
    # de quem acabou de criar o projeto.
    erro_ao_preparar: str = ""

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dono", "conexao", "repositorio_id_externo"], name="projeto_repo_unico"
            )
        ]

    def __str__(self):
        return self.nome
