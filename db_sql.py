from pathlib import Path
import sqlite3
from flask import current_app, g

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = BASE_DIR / "schema.sql"
SEED_FILE = BASE_DIR / "inclusoes.sql"
DEFAULT_DB = BASE_DIR / "drivehub.db"

STATUS_CARRO = ["disponível", "alugado", "manutenção"]
STATUS_LOCACAO = ["pendente", "ativa", "concluida"]


# ------------------------------------------------------------------ CONEXÃO
def get_db():
  """Uma conexão por requisição, guardada em g."""
  if "sql" not in g:
    g.sql = sqlite3.connect(current_app.config.get("SQL_DATABASE", str(DEFAULT_DB)))
    g.sql.row_factory = sqlite3.Row  # acesso por nome: row["modelo"]
    g.sql.execute("PRAGMA foreign_keys = ON")
  return g.sql


def close_db(_exc=None):
  """Fecha a conexão ao final da requisição."""
  conn = g.pop("sql", None)
  if conn is not None:
    conn.close()


def init_db(seed=False):
  """Recria as tabelas a partir de schema.sql (e, opcionalmente, os dados de exemplo)."""
  db = get_db()
  db.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
  if seed:
    db.executescript(SEED_FILE.read_text(encoding="utf-8"))
  db.commit()


def _where(condicoes):
  """Junta as condições em um WHERE (ou devolve vazio se não há nenhuma)."""
  return (" WHERE " + " AND ".join(condicoes)) if condicoes else ""


# ------------------------------------------------------------------ VEÍCULOS
CAR_FIELDS = ["marca", "modelo", "ano", "categoria",
              "valor_diario", "placa_veiculo", "status"]


def list_cars(search=None, status=None, categoria=None):
  """Monta o WHERE dinamicamente, mas SEMPRE com parâmetros (?)."""
  where, params = [], []
  if status:
    where.append("status = ?")
    params.append(status)
  if categoria:
    where.append("categoria = ?")
    params.append(categoria)
  if search:
    where.append("(marca LIKE ? OR modelo LIKE ? OR placa_veiculo LIKE ?)")
    params += [f"%{search}%"] * 3
  sql = "SELECT * FROM cars" + _where(where) + " ORDER BY marca, modelo"
  return get_db().execute(sql, params).fetchall()


def list_cars_for_rental(incluir_id=None):
  """Carros que podem ser reservados (tudo, menos os em manutenção).
  incluir_id mantém na lista o carro de uma locação que está sendo editada."""
  return get_db().execute(
      "SELECT * FROM cars WHERE status <> 'manutenção' OR id = ? ORDER BY marca, modelo",
      (incluir_id,),
  ).fetchall()


def list_categories():
  rows = get_db().execute(
      "SELECT DISTINCT categoria FROM cars "
      "WHERE categoria IS NOT NULL AND categoria <> '' ORDER BY categoria"
  ).fetchall()
  return [r["categoria"] for r in rows]


def get_car(car_id):
  return get_db().execute("SELECT * FROM cars WHERE id = ?", (car_id,)).fetchone()


def create_car(data):
  db = get_db()
  placeholders = ", ".join("?" for _ in CAR_FIELDS)
  cur = db.execute(
      f"INSERT INTO cars ({', '.join(CAR_FIELDS)}) VALUES ({placeholders})",
      [data.get(f) for f in CAR_FIELDS],
  )
  db.commit()
  return cur.lastrowid


def update_car(car_id, data):
  """Atualiza só os campos enviados. Os nomes de coluna vêm da lista fixa
  CAR_FIELDS (nunca do usuário), por isso o f-string aqui é seguro."""
  fields = [f for f in CAR_FIELDS if f in data]
  if not fields:
    return
  sets = ", ".join(f"{f} = ?" for f in fields)
  db = get_db()
  db.execute(f"UPDATE cars SET {sets} WHERE id = ?", [data[f] for f in fields] + [car_id])
  db.commit()


def delete_car(car_id):
  """As locações do carro somem junto (ON DELETE CASCADE)."""
  db = get_db()
  db.execute("DELETE FROM cars WHERE id = ?", (car_id,))
  db.commit()


# ------------------------------------------------------------------ CLIENTES E ATENDENTES
def list_customers():
  return get_db().execute("SELECT * FROM customers ORDER BY nome").fetchall()


def get_customer(customer_id):
  return get_db().execute(
      "SELECT * FROM customers WHERE id = ?", (customer_id,)
  ).fetchone()


def list_employees():
  # sem a coluna senha, que não precisa sair do banco
  return get_db().execute("SELECT id, nome, cargo FROM employees ORDER BY nome").fetchall()


def get_employee(employee_id):
  return get_db().execute(
      "SELECT id, nome, cargo FROM employees WHERE id = ?", (employee_id,)
  ).fetchone()


# ------------------------------------------------------------------ LOCAÇÕES
RENTAL_SELECT = """
  SELECT r.*,
         CAST(julianday(r.data_devolucao) - julianday(r.data_retirada) AS INTEGER) AS dias,
         c.marca, c.modelo, c.placa_veiculo, c.valor_diario, c.status AS car_status,
         cu.nome AS cliente, cu.cpf AS cliente_cpf, cu.telefone AS cliente_telefone,
         e.nome AS atendente
  FROM rentals r
  JOIN cars c       ON c.id  = r.car_id          -- toda locação TEM carro
  JOIN customers cu ON cu.id = r.customer_id     -- e cliente
  LEFT JOIN employees e ON e.id = r.employee_id  -- mas pode não ter atendente
"""


def list_rentals(car_id=None, status=None, search=None, limit=None):
  """Locações já com carro, cliente e atendente (JOINs), com filtros opcionais."""
  where, params = [], []
  if car_id:
    where.append("r.car_id = ?")
    params.append(car_id)
  if status:
    where.append("r.status = ?")
    params.append(status)
  if search:
    where.append("(cu.nome LIKE ? OR c.marca LIKE ? OR c.modelo LIKE ? "
                 "OR c.placa_veiculo LIKE ?)")
    params += [f"%{search}%"] * 4
  sql = RENTAL_SELECT + _where(where) + " ORDER BY r.data_retirada DESC, r.id DESC"
  if limit:
    sql += " LIMIT ?"
    params.append(limit)
  return get_db().execute(sql, params).fetchall()


def get_rental(rental_id):
  return get_db().execute(RENTAL_SELECT + " WHERE r.id = ?", (rental_id,)).fetchone()


RENTAL_FIELDS = ["car_id", "customer_id", "employee_id",
                 "data_retirada", "data_devolucao", "preco", "status"]


def car_has_conflict(car_id, retirada, devolucao, ignorar=None):
  """True se o carro já tem locação pendente/ativa que se sobrepõe ao período.
  ignorar = id de uma locação que não conta (a que está sendo editada)."""
  sql = """SELECT 1 FROM rentals
           WHERE car_id = ?
             AND status IN ('pendente', 'ativa')
             AND data_retirada < ?
             AND data_devolucao > ?"""
  params = [car_id, devolucao, retirada]
  if ignorar:
    sql += " AND id <> ?"
    params.append(ignorar)
  return get_db().execute(sql + " LIMIT 1", params).fetchone() is not None


def car_has_active_rental(car_id, ignorar=None):
  sql = "SELECT 1 FROM rentals WHERE car_id = ? AND status = 'ativa'"
  params = [car_id]
  if ignorar:
    sql += " AND id <> ?"
    params.append(ignorar)
  return get_db().execute(sql + " LIMIT 1", params).fetchone() is not None


def _sincronizar_carro(db, car_id):
  """Deixa o status do carro coerente com as locações dele:
  com locação ativa vira 'alugado'; sem nenhuma volta a 'disponível'.
  Carro em manutenção nunca é alterado."""
  if car_has_active_rental(car_id):
    db.execute("UPDATE cars SET status = 'alugado' WHERE id = ? AND status = 'disponível'",
               (car_id,))
  else:
    db.execute("UPDATE cars SET status = 'disponível' WHERE id = ? AND status = 'alugado'",
               (car_id,))


def create_rental(data):
  db = get_db()
  placeholders = ", ".join("?" for _ in RENTAL_FIELDS)
  cur = db.execute(
      f"INSERT INTO rentals ({', '.join(RENTAL_FIELDS)}) VALUES ({placeholders})",
      [data.get(f) for f in RENTAL_FIELDS],
  )
  _sincronizar_carro(db, data["car_id"])
  db.commit()
  return cur.lastrowid


def update_rental(rental_id, data):
  """Atualiza só os campos enviados (nomes de coluna vêm de RENTAL_FIELDS,
  nunca do usuário) e reajusta o status dos carros envolvidos."""
  fields = [f for f in RENTAL_FIELDS if f in data]
  if not fields:
    return
  db = get_db()
  carro_antigo = get_rental(rental_id)["car_id"]
  sets = ", ".join(f"{f} = ?" for f in fields)
  db.execute(f"UPDATE rentals SET {sets} WHERE id = ?",
             [data[f] for f in fields] + [rental_id])
  for car_id in {carro_antigo, get_rental(rental_id)["car_id"]}:
    _sincronizar_carro(db, car_id)
  db.commit()


def set_rental_status(rental_id, novo_status):
  """Atalho do quadro: muda só o status (pendente -> ativa -> concluida)."""
  update_rental(rental_id, {"status": novo_status})


def delete_rental(rental_id):
  db = get_db()
  car_id = get_rental(rental_id)["car_id"]
  db.execute("DELETE FROM rentals WHERE id = ?", (rental_id,))
  _sincronizar_carro(db, car_id)
  db.commit()


# ------------------------------------------------------------------ TOTAIS
def board_stats(car_id):
  """Quantas locações e quanto dinheiro por status (para o quadro do veículo)."""
  rows = get_db().execute(
      """
      SELECT status, COUNT(*) AS qtd, COALESCE(SUM(preco), 0) AS total
      FROM rentals WHERE car_id = ?
      GROUP BY status
      """,
      (car_id,),
  ).fetchall()
  stats = {s: {"qtd": 0, "total": 0} for s in STATUS_LOCACAO}
  for r in rows:
    stats[r["status"]] = {"qtd": r["qtd"], "total": r["total"]}
  return stats


def fleet_summary():
  """Números do painel inicial: situação da frota e das locações."""
  db = get_db()
  frota = db.execute(
      """
      SELECT COUNT(*) AS total,
             COALESCE(SUM(status = 'disponível'), 0) AS disponiveis,
             COALESCE(SUM(status = 'alugado'), 0)    AS alugados,
             COALESCE(SUM(status = 'manutenção'), 0) AS manutencao
      FROM cars
      """
  ).fetchone()
  rows = db.execute(
      """
      SELECT status, COUNT(*) AS qtd, COALESCE(SUM(preco), 0) AS total
      FROM rentals GROUP BY status
      """
  ).fetchall()
  locacoes = {s: {"qtd": 0, "total": 0} for s in STATUS_LOCACAO}
  for r in rows:
    locacoes[r["status"]] = {"qtd": r["qtd"], "total": r["total"]}
  return {**dict(frota), "locacoes": locacoes,
          "total_locacoes": sum(v["qtd"] for v in locacoes.values())}
