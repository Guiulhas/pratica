import re

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Cliente, Movimentacao, Vaga, Veiculo


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ("id", "nome", "email", "telefone")


class VeiculoSerializer(serializers.ModelSerializer):
    placa = serializers.CharField(max_length=10)

    class Meta:
        model = Veiculo
        fields = ("id", "cliente", "placa", "modelo")

    def validate_placa(self, value):
        placa = value.upper().replace("-", "").replace(" ", "")
        if not re.fullmatch(r"[A-Z]{3}[0-9][A-Z0-9][0-9]{2}", placa):
            raise serializers.ValidationError("Informe uma placa brasileira válida.")
        UniqueValidator(queryset=Veiculo.objects.all())(placa, self.fields["placa"])
        return placa


class VagaSerializer(serializers.ModelSerializer):
    disponivel = serializers.BooleanField(read_only=True)

    class Meta:
        model = Vaga
        fields = ("id", "codigo", "disponivel")

    def to_representation(self, instance):
        if not hasattr(instance, "disponivel"):
            instance.disponivel = not instance.movimentacoes.filter(saida__isnull=True).exists()
        return super().to_representation(instance)


class MovimentacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movimentacao
        fields = ("id", "veiculo", "vaga", "entrada", "saida")
        read_only_fields = ("entrada", "saida")
