# 💕 Nossa História — Guilherme & Julia

Site em **Flask + SQLite** (o banco é um arquivo, não precisa instalar nada).

- Qualquer pessoa vê o site, **curte (♥) e comenta sem login**.
- Só vocês dois (login) podem **postar fotos, vídeos e cartinhas** e apagar posts/comentários.
- Contador em tempo real desde **11/07/2026 às 22:30** (horário de Brasília).
- Feito primeiro para celular.

## Rodar no VS Code (teste no seu PC)

Abra a pasta `nossa-historia` no VS Code, abra o terminal (Ctrl + ') e rode:

```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python criar_usuarios.py       # define as senhas de vocês dois
python app.py
```

Abra http://127.0.0.1:5000 — para entrar: **Área do casal** (usuários `guilherme` e `julia`).

## Publicar no PythonAnywhere

1. Crie a conta em pythonanywhere.com (plano gratuito serve).
2. Aba **Files** → envie o `nossa-historia.zip` para `/home/SEU_USUARIO/`.
3. Aba **Consoles** → **Bash** e rode:
   ```bash
   unzip nossa-historia.zip
   cd nossa-historia
   pip3 install --user -r requirements.txt
   python3 criar_usuarios.py
   ```
4. Aba **Web** → **Add a new web app** → *Manual configuration* → escolha a versão do Python.
5. Em **Code → Source code**, coloque: `/home/SEU_USUARIO/nossa-historia`
6. Clique no link do **WSGI configuration file**, apague tudo e cole:
   ```python
   import sys
   path = '/home/SEU_USUARIO/nossa-historia'
   if path not in sys.path:
       sys.path.insert(0, path)
   from app import app as application
   ```
7. Clique em **Reload**. O site fica em `https://SEU_USUARIO.pythonanywhere.com`.

Dicas:
- No plano gratuito, a cada ~3 meses entre na aba **Web** e clique em **Run until 3 months from today**, senão o site sai do ar.
- O espaço grátis é de 512 MB: vídeos grandes enchem rápido. Fotos são reduzidas automaticamente.
- Seu banco fica em `data/nossa_historia.db` e as fotos/vídeos em `uploads/`. Faça backup baixando essas duas pastas.

## Personalizar
No topo do `app.py`: nomes, data/hora do namoro e a frase da tela inicial.
