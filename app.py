from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coopex.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# --- MODELOS ---

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # master, admin, cooperado
    intervalo_inicio = db.Column(db.String(10))  # só usado para admin
    intervalo_fim = db.Column(db.String(10))     # só usado para admin

    def set_password(self, senha):
        self.password_hash = generate_password_hash(senha)
    def check_password(self, senha):
        return check_password_hash(self.password_hash, senha)

class Valor(db.Model):
    __tablename__ = 'valores'
    id = db.Column(db.Integer, primary_key=True)
    cooperado_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)
    turno = db.Column(db.String(30), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # valor ou desconto
    criado_por = db.Column(db.Integer, db.ForeignKey('users.id'))  # quem lançou

    cooperado = db.relationship('User', foreign_keys=[cooperado_id])
    criador = db.relationship('User', foreign_keys=[criado_por])

# --- LOGIN MANAGER ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- CRIA USUÁRIO MASTER AUTOMATICAMENTE ---
@app.before_first_request
def criar_master_default():
    if not User.query.filter_by(tipo='master').first():
        master = User(
            nome='Master',
            username='coopex',
            tipo='master',
            intervalo_inicio=None,
            intervalo_fim=None,
        )
        master.set_password('coopex05289')
        db.session.add(master)
        db.session.commit()
        print('Usuário master padrão criado: login "coopex" / senha "coopex05289"')

# --- CRIA TABELAS SE NÃO EXISTIREM ---
with app.app_context():
    db.create_all()

# --- AUXILIARES ---
dias = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']
dias_label = {'seg':'Segunda', 'ter':'Terça', 'qua':'Quarta', 'qui':'Quinta',
              'sex':'Sexta', 'sab':'Sábado', 'dom':'Domingo'}

# --- ROTAS ---

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        senha = request.form["senha"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(senha):
            login_user(user)
            if user.tipo == 'master':
                return redirect(url_for('painel_master'))
            elif user.tipo == 'admin':
                return redirect(url_for('painel_admin'))
            elif user.tipo == 'cooperado':
                return redirect(url_for('painel_cooperado'))
            else:
                flash("Tipo de usuário desconhecido!", "danger")
        else:
            flash("Usuário ou senha inválidos!", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# PAINEL MASTER
@app.route("/painel_master")
@login_required
def painel_master():
    if current_user.tipo != 'master':
        return redirect(url_for('login'))
    admins = User.query.filter_by(tipo='admin').all()
    cooperados = User.query.filter_by(tipo='cooperado').all()
    valores = Valor.query.order_by(Valor.data.desc()).all()
    
    # Relatório por admin (quem lançou)
    relatorio_admins = {}
    for admin in admins:
        lancamentos = [v for v in valores if v.criador and v.criador.id == admin.id]
        total_valor = sum(v.valor for v in lancamentos if v.tipo == 'valor')
        total_desconto = sum(v.valor for v in lancamentos if v.tipo == 'desconto')
        relatorio_admins[admin] = {
            'lancamentos': lancamentos,
            'total_valor': total_valor,
            'total_desconto': total_desconto,
            'total_liquido': total_valor - total_desconto,
        }
    return render_template(
        "painel_master.html",
        admins=admins,
        cooperados=cooperados,
        valores=valores,
        relatorio_admins=relatorio_admins,
        dias_label=dias_label
    )

# PAINEL ADMIN
@app.route("/painel_admin")
@login_required
def painel_admin():
    if current_user.tipo != 'admin':
        return redirect(url_for('login'))
    cooperados = User.query.filter_by(tipo='cooperado').all()
    valores = Valor.query.order_by(Valor.data.desc()).all()
    return render_template(
        "painel_admin.html",
        cooperados=cooperados,
        valores=valores,
        admin=current_user
    )

# PAINEL COOPERADO
@app.route("/painel_cooperado")
@login_required
def painel_cooperado():
    if current_user.tipo != 'cooperado':
        return redirect(url_for('login'))
    valores = Valor.query.filter_by(cooperado_id=current_user.id).order_by(Valor.data.desc()).all()
    return render_template(
        "painel_cooperado.html",
        valores=valores
    )

# CADASTRO DE ADMIN (apenas master pode)
@app.route("/cadastro_admin", methods=["GET", "POST"])
@login_required
def cadastro_admin():
    if current_user.tipo != 'master':
        return redirect(url_for('login'))
    if request.method == "POST":
        nome = request.form["nome"]
        username = request.form["username"]
        senha = request.form["senha"]
        intervalo_inicio = request.form["intervalo_inicio"]
        intervalo_fim = request.form["intervalo_fim"]
        if User.query.filter_by(username=username).first():
            flash("Já existe um usuário com esse login!", "danger")
        else:
            admin = User(
                nome=nome,
                username=username,
                tipo='admin',
                intervalo_inicio=intervalo_inicio,
                intervalo_fim=intervalo_fim,
            )
            admin.set_password(senha)
            db.session.add(admin)
            db.session.commit()
            flash("Admin cadastrado com sucesso!", "success")
            return redirect(url_for('painel_master'))
    return render_template("cadastro_admin.html", dias=dias, dias_label=dias_label)

# CADASTRO DE COOPERADO (master ou admin pode)
@app.route("/cadastro_cooperado", methods=["GET", "POST"])
@login_required
def cadastro_cooperado():
    if current_user.tipo not in ['master', 'admin']:
        return redirect(url_for('login'))
    if request.method == "POST":
        nome = request.form["nome"]
        username = request.form["username"]
        senha = request.form["senha"]
        if User.query.filter_by(username=username).first():
            flash("Já existe um usuário com esse login!", "danger")
        else:
            cooperado = User(
                nome=nome,
                username=username,
                tipo='cooperado'
            )
            cooperado.set_password(senha)
            db.session.add(cooperado)
            db.session.commit()
            flash("Cooperado cadastrado com sucesso!", "success")
            if current_user.tipo == 'admin':
                return redirect(url_for('painel_admin'))
            else:
                return redirect(url_for('painel_master'))
    return render_template("cadastro_cooperado.html")

# CADASTRO DE VALOR/DESCONTO (master ou admin pode)
@app.route("/cadastro_valor", methods=["GET", "POST"])
@login_required
def cadastro_valor():
    if current_user.tipo not in ['master', 'admin']:
        return redirect(url_for('login'))
    cooperados = User.query.filter_by(tipo='cooperado').all()
    if request.method == "POST":
        cooperado_id = request.form["cooperado_id"]
        data_str = request.form["data"]
        turno = request.form["turno"]
        tipo = request.form["tipo"]
        valor_br = request.form["valor"]
        # Converte valor: "R$ 1.234,56" -> float(1234.56)
        valor_num = float(valor_br.replace('R$', '').replace('.', '').replace(',', '.').strip())
        try:
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
        except:
            flash("Data inválida!", "danger")
            return render_template("cadastro_valor.html", cooperados=cooperados, now=datetime.now)
        novo = Valor(
            cooperado_id=cooperado_id,
            valor=valor_num,
            data=data,
            turno=turno,
            tipo=tipo,
            criado_por=current_user.id
        )
        db.session.add(novo)
        db.session.commit()
        flash("Lançamento salvo com sucesso!", "success")
        if current_user.tipo == 'admin':
            return redirect(url_for('painel_admin'))
        else:
            return redirect(url_for('painel_master'))
    return render_template("cadastro_valor.html", cooperados=cooperados, now=datetime.now)

# --- ROTA PARA SAIR/REDIRECIONAR ---
@app.errorhandler(401)
def unauthorized(e):
    return redirect(url_for('login'))

# --- MAIN ---
if __name__ == '__main__':
    app.run(debug=True)
