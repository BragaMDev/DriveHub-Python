import sqlite3
import sys

BANCO_DADOS = "drivehub.db"  


if len(sys.argv) < 2:
  print("Uso correto: python executar.py schema.sql")
  sys.exit(1)

conn = sqlite3.connect(BANCO_DADOS)
conn.execute("PRAGMA foreign_keys = ON")  

try:
  with open(sys.argv[1], encoding="utf-8") as f:
    texto = f.read()
except FileNotFoundError:
  print(f"ERRO: O arquivo '{sys.argv[1]}' não foi encontrado.")
  sys.exit(1)


linhas = [l for l in texto.splitlines() if not l.strip().startswith("--")]
comandos = [c.strip() for c in "\n".join(linhas).split(";") if c.strip()]


for comando in comandos:
  print(">>", comando.splitlines()[0][:70])
  try:
    cur = conn.execute(comando)

    if cur.description:  
      print("\n" + " | ".join(col[0] for col in cur.description))
      for linha in cur.fetchall():
        print("\n" + " | ".join(str(v) for v in linha))
    else:
      print(f"\nOK ({cur.rowcount} linha(s) afetada(s))")

  except sqlite3.Error as erro:
    print(f"\nERRO: {erro}")

conn.commit()
conn.close()
print("\nProcesso concluído com sucesso!")