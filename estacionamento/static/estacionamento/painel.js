const acesso = document.querySelector("#acesso");
const painel = document.querySelector("#painel");
const sair = document.querySelector("#sair");
const mensagem = document.querySelector("#mensagem");
const conteudo = document.querySelector("#conteudo");
const menu = [...painel.querySelectorAll("[data-tela]")];
let token = "";
let tela = "movimentacoes";
let versao = 0;

function elemento(tag, texto, classe) {
    const node = document.createElement(tag);
    if (texto) node.textContent = texto;
    if (classe) node.className = classe;
    return node;
}

function avisar(texto, erro = false) {
    mensagem.textContent = texto;
    mensagem.classList.toggle("erro", erro);
    mensagem.hidden = !texto;
}

async function api(recurso, dados) {
    const headers = { Accept: "application/json" };
    if (token) headers.Authorization = "Token " + token;
    if (dados) headers["Content-Type"] = "application/json";
    const resposta = await fetch("/api/" + recurso + "/", {
        headers,
        method: dados ? "POST" : "GET",
        body: dados ? JSON.stringify(dados) : undefined,
    });
    const resultado = await resposta.json().catch(() => null);
    if (resposta.ok) return resultado;
    const detalhe = resultado && Object.values(resultado).flat().find(valor => typeof valor === "string");
    throw new Error(detalhe || "Não foi possível concluir a operação.");
}

function cartao(titulo, corpo) {
    const secao = elemento("section", "", "cartao");
    secao.append(elemento("h2", titulo), corpo);
    conteudo.append(secao);
}

function formulario(titulo, campos, botao, recurso, sucesso) {
    const form = elemento("form");
    let podeEnviar = true;
    for (const campo of campos) {
        const label = elemento("label", campo.label);
        const controle = elemento(campo.opcoes ? "select" : "input");
        controle.name = campo.nome;
        controle.required = !campo.opcional;
        if (campo.opcoes) {
            const placeholder = elemento("option", campo.vazio || "Selecione");
            placeholder.value = "";
            controle.append(placeholder);
            for (const [id, nome] of campo.opcoes) {
                const opcao = elemento("option", nome);
                opcao.value = id;
                controle.append(opcao);
            }
            podeEnviar = podeEnviar && campo.opcoes.length > 0;
        } else {
            controle.type = campo.tipo || "text";
            if (campo.max) controle.maxLength = campo.max;
        }
        label.append(controle);
        form.append(label);
    }
    const enviar = elemento("button", botao);
    enviar.disabled = !podeEnviar;
    form.append(enviar);
    form.addEventListener("submit", evento => {
        evento.preventDefault();
        salvar(enviar, recurso, Object.fromEntries(new FormData(form)), sucesso);
    });
    cartao(titulo, form);
}

async function salvar(botao, recurso, dados, sucesso) {
    const atual = versao;
    botao.disabled = true;
    avisar("");
    try {
        await api(recurso, dados);
        if (atual === versao) {
            avisar(sucesso);
            await abrir(tela, false);
        }
    } catch (erro) {
        if (atual === versao) avisar(erro.message, true);
    } finally {
        botao.disabled = false;
    }
}

function listar(titulo, dados, vazio, montar) {
    const lista = elemento("ul", "", "lista");
    if (!dados.length) lista.append(elemento("li", vazio));
    for (const dado of dados) {
        const item = elemento("li");
        montar(item, dado);
        lista.append(item);
    }
    cartao(titulo, lista);
}

function descricao(item, titulo, detalhe) {
    const bloco = elemento("div");
    bloco.append(elemento("strong", titulo));
    if (detalhe) bloco.append(elemento("small", detalhe));
    item.append(bloco);
}

const horario = valor => new Date(valor).toLocaleString("pt-BR");

const telas = {
    clientes: {
        recursos: ["clientes"],
        mostrar(clientes) {
            formulario("Cadastrar cliente", [
                { nome: "nome", label: "Nome", max: 120 },
                { nome: "email", label: "E-mail", tipo: "email" },
                { nome: "telefone", label: "Telefone (opcional)", tipo: "tel", max: 25, opcional: true },
            ], "Cadastrar cliente", "clientes", "Cliente cadastrado.");
            listar("Clientes cadastrados", clientes, "Nenhum cliente cadastrado.", (item, cliente) => {
                descricao(item, cliente.nome, [cliente.email, cliente.telefone].filter(Boolean).join(" · "));
            });
        },
    },
    veiculos: {
        recursos: ["veiculos", "clientes"],
        mostrar(veiculos, clientes) {
            const nomes = new Map(clientes.map(cliente => [cliente.id, cliente.nome]));
            formulario("Cadastrar veículo", [
                { nome: "cliente", label: "Cliente", opcoes: [...nomes], vazio: clientes.length ? "Selecione" : "Cadastre um cliente primeiro" },
                { nome: "placa", label: "Placa", max: 10 },
                { nome: "modelo", label: "Modelo", max: 100 },
            ], "Cadastrar veículo", "veiculos", "Veículo cadastrado.");
            listar("Veículos cadastrados", veiculos, "Nenhum veículo cadastrado.", (item, veiculo) => {
                descricao(item, veiculo.placa, [veiculo.modelo, nomes.get(veiculo.cliente)].filter(Boolean).join(" · "));
            });
        },
    },
    vagas: {
        recursos: ["vagas"],
        mostrar(vagas) {
            formulario("Cadastrar vaga", [{ nome: "codigo", label: "Código", max: 20 }],
                "Cadastrar vaga", "vagas", "Vaga cadastrada.");
            const livres = vagas.filter(vaga => vaga.disponivel).length;
            listar(`Vagas cadastradas · ${livres} livres de ${vagas.length}`, vagas, "Nenhuma vaga cadastrada.", (item, vaga) => {
                descricao(item, vaga.codigo);
                item.append(elemento("span", vaga.disponivel ? "Livre" : "Ocupada", vaga.disponivel ? "estado livre" : "estado"));
            });
        },
    },
    movimentacoes: {
        recursos: ["movimentacoes", "veiculos", "vagas"],
        mostrar(movimentacoes, veiculos, vagas) {
            const abertas = movimentacoes.filter(movimentacao => !movimentacao.saida);
            const estacionados = new Set(abertas.map(movimentacao => movimentacao.veiculo));
            const placas = new Map(veiculos.map(veiculo => [veiculo.id, veiculo.placa]));
            const codigos = new Map(vagas.map(vaga => [vaga.id, vaga.codigo]));
            const fora = [...placas].filter(([id]) => !estacionados.has(id));
            const livres = vagas.filter(vaga => vaga.disponivel).map(vaga => [vaga.id, vaga.codigo]);
            formulario("Registrar entrada", [
                { nome: "veiculo", label: "Veículo", opcoes: fora, vazio: fora.length ? "Selecione" : "Nenhum veículo disponível" },
                { nome: "vaga", label: "Vaga livre", opcoes: livres, vazio: livres.length ? "Selecione" : "Nenhuma vaga livre" },
            ], "Registrar entrada", "movimentacoes", "Entrada registrada.");
            listar("Veículos no estacionamento", abertas, "Nenhum veículo estacionado.", (item, movimento) => {
                descricao(item, placas.get(movimento.veiculo), `Vaga ${codigos.get(movimento.vaga)} · Entrada: ${horario(movimento.entrada)}`);
                const botao = elemento("button", "Registrar saída", "secundario");
                botao.addEventListener("click", () =>
                    salvar(botao, `movimentacoes/${movimento.id}/saida`, {}, "Saída registrada. A vaga está livre."));
                item.append(botao);
            });
            listar("Histórico de saídas", movimentacoes.filter(movimento => movimento.saida), "Nenhuma saída registrada.", (item, movimento) => {
                descricao(item, placas.get(movimento.veiculo),
                    `Vaga ${codigos.get(movimento.vaga)} · Entrada: ${horario(movimento.entrada)} · Saída: ${horario(movimento.saida)}`);
            });
        },
    },
};

async function abrir(destino, limpar = true) {
    tela = destino;
    const atual = ++versao;
    const pagina = telas[tela];
    if (limpar) avisar("");
    for (const botao of menu) {
        if (botao.dataset.tela === tela) {
            botao.setAttribute("aria-current", "page");
            document.querySelector("#titulo").textContent = botao.textContent;
        } else {
            botao.removeAttribute("aria-current");
        }
    }
    conteudo.replaceChildren(elemento("p", "Carregando…"));
    try {
        const dados = await Promise.all(pagina.recursos.map(recurso => api(recurso)));
        if (atual !== versao) return;
        conteudo.replaceChildren();
        pagina.mostrar(...dados);
    } catch (erro) {
        if (atual !== versao) return;
        const tentar = elemento("button", "Tentar novamente", "secundario");
        tentar.addEventListener("click", () => abrir(tela));
        conteudo.replaceChildren(tentar);
        avisar(erro.message, true);
    }
}

for (const botao of menu) botao.addEventListener("click", () => abrir(botao.dataset.tela));

document.querySelector("#login").addEventListener("submit", async evento => {
    evento.preventDefault();
    const form = evento.currentTarget;
    const botao = form.querySelector("button");
    botao.disabled = true;
    avisar("");
    try {
        const resultado = await api("token-auth", Object.fromEntries(new FormData(form)));
        token = resultado.token;
        form.reset();
        acesso.hidden = true;
        painel.hidden = false;
        sair.hidden = false;
        menu[0].focus();
        await abrir("movimentacoes");
    } catch (erro) {
        avisar(erro.message, true);
    } finally {
        botao.disabled = false;
    }
});

sair.addEventListener("click", () => {
    ++versao;
    token = "";
    conteudo.replaceChildren();
    painel.hidden = true;
    sair.hidden = true;
    acesso.hidden = false;
    acesso.querySelector("input").focus();
    avisar("");
});
