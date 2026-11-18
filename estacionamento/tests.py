from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


class EstacionamentoAPITest(APITestCase):
    def setUp(self):
        self.client.force_authenticate(get_user_model().objects.create_user(username="operador"))
        cliente = self.criar("clientes", {"nome": "Ana", "email": "ana@example.com"})
        self.veiculo = self.criar("veiculos", {"cliente": cliente["id"], "placa": "abc-1234", "modelo": "Uno"})
        self.outro_veiculo = self.criar(
            "veiculos", {"cliente": cliente["id"], "placa": "DEF1A23", "modelo": "Gol"}
        )
        self.vaga = self.criar("vagas", {"codigo": "A01"})
        self.outra_vaga = self.criar("vagas", {"codigo": "A02"})

    def criar(self, recurso, dados):
        resposta = self.client.post(f"/api/{recurso}/", dados, format="json")
        self.assertEqual(resposta.status_code, 201, resposta.data)
        return resposta.data

    def vagas_livres(self):
        resposta = self.client.get("/api/vagas/?disponivel=true")
        self.assertEqual(resposta.status_code, 200)
        return {vaga["id"] for vaga in resposta.data}

    def test_entrada_saida_e_reutilizacao_da_vaga(self):
        dados = {"veiculo": self.veiculo["id"], "vaga": self.vaga["id"]}
        self.assertEqual(self.vagas_livres(), {self.vaga["id"], self.outra_vaga["id"]})
        entrada = self.criar("movimentacoes", dados)
        self.assertTrue(entrada["entrada"])
        self.assertIsNone(entrada["saida"])
        self.assertEqual(self.vagas_livres(), {self.outra_vaga["id"]})
        ocupadas = self.client.get("/api/vagas/?disponivel=false")
        self.assertEqual([vaga["id"] for vaga in ocupadas.data], [self.vaga["id"]])

        url_saida = f"/api/movimentacoes/{entrada['id']}/saida/"
        saida = self.client.post(url_saida)
        self.assertEqual(saida.status_code, 200, saida.data)
        self.assertTrue(saida.data["saida"])
        self.assertEqual(self.client.post(url_saida).status_code, 409)
        self.assertEqual(self.vagas_livres(), {self.vaga["id"], self.outra_vaga["id"]})

        self.criar("movimentacoes", dados)
        historico = self.client.get("/api/movimentacoes/").data
        self.assertEqual(len(historico), 2)
        self.assertEqual(historico[1]["saida"], saida.data["saida"])

    def test_rejeita_vaga_ocupada_e_veiculo_que_ja_entrou(self):
        self.criar("movimentacoes", {"veiculo": self.veiculo["id"], "vaga": self.vaga["id"]})
        for dados in [
            {"veiculo": self.outro_veiculo["id"], "vaga": self.vaga["id"]},
            {"veiculo": self.veiculo["id"], "vaga": self.outra_vaga["id"]},
        ]:
            with self.subTest(dados=dados):
                self.assertEqual(self.client.post("/api/movimentacoes/", dados).status_code, 409)
        self.assertEqual(self.vagas_livres(), {self.outra_vaga["id"]})

    def test_normaliza_placa_e_rejeita_duplicatas(self):
        self.assertEqual(self.veiculo["placa"], "ABC1234")
        resposta = self.client.post("/api/veiculos/", {
            "cliente": self.veiculo["cliente"], "placa": "abc 1234", "modelo": "Celta"
        })
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("placa", resposta.data)

    def test_requer_autenticacao(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get("/api/clientes/").status_code, 401)
