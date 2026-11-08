import getpass

from django.core.management.base import BaseCommand, CommandError

from apps.donos import servicos


class Command(BaseCommand):
    help = "Cria um dono e o usuário de login dele. A senha é pedida no terminal."

    def add_arguments(self, parser):
        parser.add_argument("--nome", required=True, help="Nome do dono.")
        parser.add_argument("--usuario", required=True, help="Nome de usuário do login.")
        parser.add_argument("--email", required=True, help="E-mail do usuário.")

    def handle(self, *args, **opcoes):
        senha = getpass.getpass("Senha: ")
        if senha != getpass.getpass("Repita a senha: "):
            raise CommandError("As senhas não conferem. Rode o comando de novo.")
        try:
            membro = servicos.criar_dono(opcoes["nome"], opcoes["usuario"], opcoes["email"], senha)
        except ValueError as erro:
            raise CommandError(str(erro)) from erro
        self.stdout.write(
            self.style.SUCCESS(
                f'Dono "{membro.dono.nome}" criado com o usuário "{opcoes["usuario"]}".'
            )
        )
