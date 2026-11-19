import os
import re
import sqlite3
from datetime import date
from pathlib import Path

import click
from flask import Flask, abort, flash, redirect, render_template, request, url_for

import db_sql as sql

BASE_DIR = Path(__file__).resolve().parent

# pendente -> ativa -> concluida (o quadro e os botões só andam para frente)
TRANSICOES = {"pendente": ["ativa"], "ativa": ["concluida"], "concluida": []}
PLACA_RE = re.compile(r"^[A-Z]{3}\d[A-Z0-9]\d{2}$")  # ABC1234 ou ABC1D23 (Mercosul)


def create_app(test_config=None):
  app = Flask(__name__)

  app.config.from_mapping(
      SECRET_KEY=os.environ.get("SECRET_KEY", "dev-troque-em-producao"),
      SQL_DATABASE=os.environ.get("SQL_DATABASE", str(BASE_DIR / "drivehub.db")),
  )

  if test_config:
    app.config.update(test_config)

  app.teardown_appcontext(sql.close_db)  # fecha a conexão no fim de cada requisição

  register_cli(app)
  register_filters(app)
  register_errors(app)
  register_html_routes(app)

  return app


# ------------------------------------------------------------------ VALIDAÇÃO DOS FORMULÁRIOS
def _por_id(buscar, valor):
  """Converte o valor do formulário em int e busca no banco (None se inválido)."""
  try:
    return buscar(int(valor))
  except (TypeError, ValueError):
    return None


def carro_form_data(form, atual=None):
  """Lê e valida o formulário de veículo. Devolve (dados, erros)."""
  erros = []

  marca = (form.get("marca") or "").strip()
  modelo = (form.get("modelo") or "").strip()
  if not marca:
    erros.append("Marca é obrigatória.")
  if not modelo:
    erros.append("Modelo é obrigatório.")

  ano = None
  if (form.get("ano") or "").strip():
    try:
      ano = int(form["ano"])
      if not 1990 <= ano <= date.today().year + 1:
        raise ValueError
    except ValueError:
      erros.append("Ano inválido.")

  valor = None
  try:
    valor = round(float((form.get("valor_diario") or "").replace(",", ".")), 2)
    if valor <= 0:
      raise ValueError
  except ValueError:
    erros.append("Informe um valor de diária maior que zero.")

  placa = re.sub(r"[\s-]", "", form.get("placa_veiculo") or "").upper()
  if not PLACA_RE.match(placa):
    erros.append("Placa inválida (use o formato ABC1D23 ou ABC1234).")

  # 'alugado' é controlado pelas locações: só aparece se o carro já está assim
  status = form.get("status", "disponível")
  validos = ["disponível", "manutenção"]
  if atual and atual["status"] == "alugado":
    validos.append("alugado")
  if status not in validos:
    erros.append("Status inválido.")
  elif atual and status == "manutenção" and sql.car_has_active_rental(atual["id"]):
    erros.append("Este veículo tem uma locação ativa. Conclua-a antes de enviá-lo à manutenção.")

  dados = {
      "marca": marca, "modelo": modelo, "ano": ano,
      "categoria": (form.get("categoria") or "").strip() or None,
      "valor_diario": valor, "placa_veiculo": placa, "status": status,
  }
  return dados, erros


def locacao_form_data(form, atual=None, status_validos=("pendente", "ativa")):
  """Lê e valida o formulário de locação. Devolve (dados, erros).
  atual = a locação que está sendo editada (None quando é uma nova)."""
  erros = []
  car = _por_id(sql.get_car, form.get("car_id"))
  customer = _por_id(sql.get_customer, form.get("customer_id"))

  emp_raw = (form.get("employee_id") or "").strip()
  employee = _por_id(sql.get_employee, emp_raw) if emp_raw else None

  status = form.get("status", "pendente")
  try:
    retirada = date.fromisoformat(form.get("data_retirada", ""))
    devolucao = date.fromisoformat(form.get("data_devolucao", ""))
  except ValueError:
    retirada = devolucao = None
    erros.append("Informe as datas de retirada e devolução.")

  if car is None:
    erros.append("Escolha um veículo válido.")
  if customer is None:
    erros.append("Escolha um cliente válido.")
  if emp_raw and employee is None:
    erros.append("Atendente inválido.")
  if status not in status_validos:
    erros.append("Status inválido.")
  if retirada and devolucao and devolucao <= retirada:
    erros.append("A devolução deve ser depois da retirada.")

  if not erros and status != "concluida":
    rid = atual["id"] if atual else None
    if (atual is None or atual["car_id"] != car["id"]) and car["status"] == "manutenção":
      erros.append("Este veículo está em manutenção.")
    if (atual is None or atual["customer_id"] != customer["id"]) and not customer["habilitacao"]:
      erros.append(f"{customer['nome']} não tem habilitação cadastrada.")
    if sql.car_has_conflict(car["id"], retirada.isoformat(), devolucao.isoformat(), rid):
      erros.append("Este veículo já tem uma locação nesse período.")
    if status == "ativa" and sql.car_has_active_rental(car["id"], rid):
      erros.append("Este veículo ainda está com outra locação ativa.")

  if erros:
    return {}, erros

  dias = (devolucao - retirada).days
  mesmo_periodo = (atual is not None and atual["car_id"] == car["id"]
                   and atual["data_retirada"] == retirada.isoformat()
                   and atual["data_devolucao"] == devolucao.isoformat())
  # editar sem mexer em carro/datas preserva o preço já combinado
  preco = atual["preco"] if mesmo_periodo else round(dias * car["valor_diario"], 2)

  dados = {
      "car_id": car["id"], "customer_id": customer["id"],
      "employee_id": employee["id"] if employee else None,
      "data_retirada": retirada.isoformat(), "data_devolucao": devolucao.isoformat(),
      "preco": preco, "status": status,
      "dias": dias,  # só para a mensagem; create/update ignoram (não está em RENTAL_FIELDS)
  }
  return dados, []


# ------------------------------------------------------------------ CLI, FILTROS E ERROS
def register_cli(app):
  @app.cli.command("init-db")
  @click.option("--seed", is_flag=True, help="Também carrega os dados de inclusoes.sql.")
  def init_db_command(seed):
    """Recria as tabelas do banco SQL (APAGA os dados!)."""
    sql.init_db(seed=seed)
    click.echo("Banco SQL criado" + (" com dados de exemplo." if seed else "."))


def register_filters(app):
  @app.template_filter("data_br")
  def data_br(valor):
    """2026-06-01 -> 01/06/2026"""
    try:
      return date.fromisoformat(valor).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
      return valor or "-"

  @app.template_filter("moeda")
  def moeda(valor):
    """1234.5 -> R$ 1.234,50"""
    try:
      texto = f"{float(valor):,.2f}"
    except (TypeError, ValueError):
      return "-"
    return "R$ " + texto.replace(",", "_").replace(".", ",").replace("_", ".")


def register_errors(app):
  @app.errorhandler(404)
  def pagina_nao_encontrada(_erro):
    return render_template("404.html"), 404


# ------------------------------------------------------------------ ROTAS
def register_html_routes(app):
  register_page_routes(app)
  register_car_routes(app)
  register_rental_routes(app)


def register_page_routes(app):
  @app.route("/")
  def index():
    return render_template(
        "home.html",
        resumo=sql.fleet_summary(),
        recentes=sql.list_rentals(limit=5),
        disponiveis=sql.list_cars(status="disponível")[:5],
    )

  @app.route("/sobre")
  def sobre():
    return render_template("sobre.html")


def register_car_routes(app):
  @app.route("/frota")
  def frota():
    q = (request.args.get("q") or "").strip() or None
    status = request.args.get("status") or None
    categoria = request.args.get("categoria") or None
    return render_template(
        "frota.html", veiculos=sql.list_cars(q, status, categoria),
        categorias=sql.list_categories(), statuses=sql.STATUS_CARRO,
        q=q or "", status=status, categoria=categoria,
    )

  # Passo 6 adaptado: o "projeto" do professor é o veículo e as "issues" são as locações.
  @app.route("/veiculo/<int:car_id>")
  def veiculo_detalhe(car_id):
    carro = sql.get_car(car_id) or abort(404)
    status = request.args.get("status") or None
    if status not in sql.STATUS_LOCACAO:
      status = None
    q = (request.args.get("q") or "").strip() or None
    return render_template(
        "veiculo.html", carro=carro,
        locacoes=sql.list_rentals(car_id=car_id, status=status, search=q),
        stats=sql.board_stats(car_id), statuses=sql.STATUS_LOCACAO,
        status=status, q=q or "",
    )

  def _form_carro(carro, valores):
    status_opcoes = ["disponível", "manutenção"]
    if carro is not None and carro["status"] == "alugado":
      status_opcoes.append("alugado")
    return render_template(
        "veiculo_form.html", carro=carro, valores=valores,
        categorias=sql.list_categories(), statuses=status_opcoes,
    )

  @app.route("/veiculo/novo", methods=["GET", "POST"])
  def veiculo_novo():
    if request.method == "POST":
      dados, erros = carro_form_data(request.form)
      if not erros:
        try:
          car_id = sql.create_car(dados)
        except sqlite3.IntegrityError:
          erros.append("Já existe um veículo com essa placa.")
        else:
          flash("Veículo cadastrado!", "ok")
          return redirect(url_for("veiculo_detalhe", car_id=car_id))
      for e in erros:
        flash(e, "error")
      return _form_carro(None, request.form)
    return _form_carro(None, {})

  @app.route("/veiculo/<int:car_id>/editar", methods=["GET", "POST"])
  def veiculo_editar(car_id):
    carro = sql.get_car(car_id) or abort(404)
    if request.method == "POST":
      dados, erros = carro_form_data(request.form, atual=carro)
      if not erros:
        try:
          sql.update_car(car_id, dados)
        except sqlite3.IntegrityError:
          erros.append("Já existe outro veículo com essa placa.")
        else:
          flash("Veículo atualizado.", "ok")
          return redirect(url_for("veiculo_detalhe", car_id=car_id))
      for e in erros:
        flash(e, "error")
      return _form_carro(carro, request.form)
    return _form_carro(carro, dict(carro))

  @app.post("/veiculo/<int:car_id>/excluir")
  def veiculo_excluir(car_id):
    sql.get_car(car_id) or abort(404)
    if sql.car_has_active_rental(car_id):
      flash("Não é possível excluir: o veículo tem uma locação ativa.", "error")
      return redirect(url_for("veiculo_detalhe", car_id=car_id))
    sql.delete_car(car_id)
    flash("Veículo e suas locações foram excluídos.", "ok")
    return redirect(url_for("frota"))


def register_rental_routes(app):
  def _form_locacao(locacao, valores, statuses):
    return render_template(
        "locacao_form.html", locacao=locacao, valores=valores, statuses=statuses,
        carros=sql.list_cars_for_rental(locacao["car_id"] if locacao else None),
        clientes=sql.list_customers(), atendentes=sql.list_employees(),
    )

  def _mudar_status(rental_id, novo):
    """Regras do botão Iniciar/Concluir. Devolve a mensagem e a categoria."""
    loc = sql.get_rental(rental_id) or abort(404)
    if novo not in TRANSICOES[loc["status"]]:
      return "Essa mudança de status não é permitida.", "error"
    if novo == "ativa" and sql.car_has_active_rental(loc["car_id"], ignorar=rental_id):
      return "Este veículo ainda está com outra locação ativa.", "error"
    sql.set_rental_status(rental_id, novo)
    if novo == "ativa":
      return f"Locação #{rental_id} iniciada. Veículo marcado como alugado.", "ok"
    return f"Locação #{rental_id} concluída. Veículo liberado.", "ok"

  @app.route("/locacoes")
  def locacoes():
    q = (request.args.get("q") or "").strip() or None
    status = request.args.get("status") or None
    if status not in sql.STATUS_LOCACAO:
      status = None
    return render_template(
        "locacoes.html", locacoes=sql.list_rentals(status=status, search=q),
        resumo=sql.fleet_summary(), statuses=sql.STATUS_LOCACAO,
        status=status, q=q or "",
    )

  @app.route("/locacoes/nova", methods=["GET", "POST"])
  def locacao_nova():
    if request.method == "POST":
      dados, erros = locacao_form_data(request.form)
      if not erros:
        loc_id = sql.create_rental(dados)
        flash(f"Locação criada! {dados['dias']} diária(s) = "
              f"R$ {dados['preco']:.2f}", "ok")
        return redirect(url_for("locacao_detalhe", rental_id=loc_id))
      for e in erros:
        flash(e, "error")
      return _form_locacao(None, request.form, ["pendente", "ativa"])
    # ?car_id=3 vem do botão "Alugar" da frota e já deixa o carro escolhido
    return _form_locacao(None, {"car_id": request.args.get("car_id", "")},
                         ["pendente", "ativa"])

  @app.route("/locacoes/<int:rental_id>")
  def locacao_detalhe(rental_id):
    loc = sql.get_rental(rental_id) or abort(404)
    return render_template("locacao.html", loc=loc)

  @app.route("/locacoes/<int:rental_id>/editar", methods=["GET", "POST"])
  def locacao_editar(rental_id):
    loc = sql.get_rental(rental_id) or abort(404)
    if request.method == "POST":
      dados, erros = locacao_form_data(request.form, atual=loc,
                                       status_validos=sql.STATUS_LOCACAO)
      if not erros:
        sql.update_rental(rental_id, dados)
        flash("Locação atualizada.", "ok")
        return redirect(url_for("locacao_detalhe", rental_id=rental_id))
      for e in erros:
        flash(e, "error")
      return _form_locacao(loc, request.form, sql.STATUS_LOCACAO)
    return _form_locacao(loc, dict(loc), sql.STATUS_LOCACAO)

  @app.post("/locacoes/<int:rental_id>/status")
  def locacao_mover(rental_id):
    """Atalho do quadro: muda só o status."""
    msg, cat = _mudar_status(rental_id, request.form.get("status"))
    flash(msg, cat)
    return redirect(request.referrer or url_for("locacao_detalhe", rental_id=rental_id))

  # os botões antigos continuam funcionando, agora com as mesmas regras do quadro
  @app.post("/locacoes/<int:rental_id>/iniciar")
  def locacao_iniciar(rental_id):
    msg, cat = _mudar_status(rental_id, "ativa")
    flash(msg, cat)
    return redirect(request.referrer or url_for("locacoes"))

  @app.post("/locacoes/<int:rental_id>/concluir")
  def locacao_concluir(rental_id):
    msg, cat = _mudar_status(rental_id, "concluida")
    flash(msg, cat)
    return redirect(request.referrer or url_for("locacoes"))

  @app.post("/locacoes/<int:rental_id>/excluir")
  def locacao_excluir(rental_id):
    loc = sql.get_rental(rental_id) or abort(404)
    sql.delete_rental(rental_id)
    flash(f"Locação #{rental_id} excluída.", "ok")
    # volta para o veículo se a exclusão veio da página dele
    if request.referrer and f"/veiculo/{loc['car_id']}" in request.referrer:
      return redirect(url_for("veiculo_detalhe", car_id=loc["car_id"]))
    return redirect(url_for("locacoes"))


app = create_app()

if __name__ == "__main__":
  app.run(debug=True)
