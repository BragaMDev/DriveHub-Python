# DriveHub

Sistema web de gerenciamento de locação de veículos desenvolvido com **Python**, **Flask**, **Jinja2**, **HTML/CSS** e **SQLite**, estruturado para gerenciar frota, clientes, funcionários e locações com banco de dados relacional.

---

## Sobre o Projeto

O **DriveHub** é uma aplicação web voltada ao controle operacional de uma locadora de veículos, permitindo navegar pela página inicial, consultar e gerenciar a frota (`frota`), visualizar detalhes e formulários de veículos (`veiculo`, `veiculo_form`), administrar locações (`locacoes`, `locacao`, `locacao_form`) e acessar informações institucionais (`sobre`), além de contar com página customizada de erro `404`.

---

## Tecnologias Utilizadas

* **Backend:** Python, Flask
* **Frontend:** HTML5, CSS3 (`static/style.css`), templates Jinja2, macros reutilizáveis (`templates/_macros.html`) e favicon personalizado (`static/DriveHub Favicon.png`)
* **Banco de Dados:** SQLite (`drivehub.db`) com scripts SQL (`schema.sql`, `inclusoes.sql`, `alteracoes.sql`, `consultas.sql`) e camada de acesso em `db_sql.py`
* **Controle de Versão:** Git e GitHub

---

## Estrutura do Projeto

```text
DriveHub-Python/
├── app.py                  
├── db_sql.py               
├── executar.py             
├── drivehub.db            
├── schema.sql             
├── inclusoes.sql           
├── alteracoes.sql          
├── consultas.sql           
├── requirements.txt        
├── Respostas-Teórica.txt  
├── static/
│   ├── DriveHub Favicon.png
│   └── style.css
└── templates/
    ├── _macros.html
    ├── 404.html
    ├── base.html
    ├── frota.html
    ├── home.html
    ├── locacao.html
    ├── locacao_form.html
    ├── locacoes.html
    ├── sobre.html
    ├── veiculo.html
    └── veiculo_form.html
