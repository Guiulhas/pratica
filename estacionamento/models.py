from django.db import models
from django.db.models import Q


class Cliente(models.Model):
    nome = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=25, blank=True)

    class Meta:
        ordering = ("id",)


class Veiculo(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="veiculos")
    placa = models.CharField(max_length=7, unique=True)
    modelo = models.CharField(max_length=100)

    class Meta:
        ordering = ("id",)


class Vaga(models.Model):
    codigo = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ("codigo",)


class Movimentacao(models.Model):
    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="movimentacoes")
    vaga = models.ForeignKey(Vaga, on_delete=models.PROTECT, related_name="movimentacoes")
    entrada = models.DateTimeField(auto_now_add=True)
    saida = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-entrada", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=["veiculo"], condition=Q(saida__isnull=True),
                name="estacionamento_veiculo_uma_entrada_aberta",
            ),
            models.UniqueConstraint(
                fields=["vaga"], condition=Q(saida__isnull=True),
                name="estacionamento_vaga_uma_entrada_aberta",
            ),
        ]
