from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef
from django.db.models.functions import Now
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Cliente, Movimentacao, Vaga, Veiculo
from .serializers import ClienteSerializer, MovimentacaoSerializer, VagaSerializer, VeiculoSerializer


class Conflito(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflito"


class CadastroViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin, viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]


class ClienteViewSet(CadastroViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer


class VeiculoViewSet(CadastroViewSet):
    queryset = Veiculo.objects.all()
    serializer_class = VeiculoSerializer


class VagaViewSet(CadastroViewSet):
    queryset = Vaga.objects.annotate(
        disponivel=~Exists(Movimentacao.objects.filter(vaga_id=OuterRef("pk"), saida__isnull=True))
    )
    serializer_class = VagaSerializer

    @extend_schema(parameters=[
        OpenApiParameter("disponivel", bool, description="Filtra vagas livres (true) ou ocupadas (false)."),
    ])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def filter_queryset(self, queryset):
        if self.action != "list":
            return queryset
        valor = self.request.query_params.get("disponivel")
        if valor is None:
            return queryset
        if valor.lower() not in {"true", "false"}:
            raise ValidationError({"disponivel": "Use true ou false."})
        return queryset.filter(disponivel=valor.lower() == "true")


class MovimentacaoViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Movimentacao.objects.all()
    serializer_class = MovimentacaoSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            dados = serializer.validated_data
            abertas = Movimentacao.objects.filter(saida__isnull=True)
            if abertas.filter(veiculo=dados["veiculo"]).exists():
                raise Conflito("O veículo já tem uma entrada em aberto.")
            if abertas.filter(vaga=dados["vaga"]).exists():
                raise Conflito("A vaga já está ocupada.")
            raise Conflito("A entrada não pôde ser registrada. Confira o veículo e a vaga.")

    @extend_schema(request=None, responses={200: MovimentacaoSerializer})
    @action(detail=True, methods=["post"])
    def saida(self, request, pk=None):
        movimentacao = self.get_object()
        atualizadas = self.get_queryset().filter(pk=movimentacao.pk, saida__isnull=True).update(saida=Now())
        if not atualizadas:
            raise Conflito("A saída desta movimentação já foi registrada.")
        movimentacao.refresh_from_db()
        return Response(self.get_serializer(movimentacao).data)
