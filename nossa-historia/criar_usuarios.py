"""Cria (ou troca a senha d)os dois logins do site: guilherme e julia.
Uso:  python criar_usuarios.py
"""
import getpass
import sqlite3

from werkzeug.security import generate_password_hash

from app import DB_PATH, NOME_1, NOME_2, init_db

init_db()
con = sqlite3.connect(DB_PATH)

for usuario, nome in (("guilherme", NOME_1), ("julia", NOME_2)):
    resp = input(f"\nDefinir senha de {nome} (usuário: {usuario})? [S/n] ").strip().lower()
    if resp == "n":
        continue
    while True:
        s1 = getpass.getpass(f"Senha de {nome} (mín. 8 caracteres): ")
        s2 = getpass.getpass("Repita a senha: ")
        if len(s1) < 8:
            print("  Muito curta, use pelo menos 8 caracteres.")
        elif s1 != s2:
            print("  As senhas não conferem, tente de novo.")
        else:
            break
    con.execute(
        "INSERT INTO users(username, display_name, password_hash) VALUES(?,?,?) "
        "ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash, display_name=excluded.display_name",
        (usuario, nome, generate_password_hash(s1)))
    con.commit()
    print(f"  ✔ {nome} pronto(a)!")

con.close()
print("\nPronto! Agora é só rodar o site.")
