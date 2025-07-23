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
    intervalo_inicio = db.Column(db.String(10))
    intervalo_fim = db.Column(db.String(10))

    def set_password(self, senha):
        self.password_hash = generate_password_hash(senha)
    def check_password(self, senha):
        return check_password_hash(self.password_hash, senha)

class TipoLancamento(db.Model):
    __tablename__ = 'tipos_lancamento'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # valor ou desconto

class Valor(db.Model):
    __tablename__ = 'valores'
    id = db.Column(db.Integer, primary_key=True)
    cooperado_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tipo_lancamento_id = db.Column(db.Integer, db.ForeignKey('tipos_lancamento.id'))
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)
    turno = db.Column(db.String(30), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # valor ou desconto
    criado_por = db.Column(db.Integer, db.ForeignKey('users.id'))

    cooperado = db.relationship('User', foreign_keys=[cooperado_id])
    criador = db.relationship('User', foreign_keys=[criado_por])
    tipo_lancamento = db.relationship('TipoLancamento', foreign_keys=[tipo_lancamento_id])

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

dias = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']
dias_label = {'seg':'Segunda', 'ter':'Terça', 'qua':'Quarta', 'qui':'Quinta',
              'sex':'Sexta', 'sab':'Sábado', 'dom':'Domingo'}

with app.app_context():
    db.create_all()
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

# ---- ROTAS ----

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
    return render_template("login.html", now=datetime.now)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Painel MASTER ---
@app.route("/painel_master")
@login_required
def painel_master():
    if current_user.tipo != 'master':
        return redirect(url_for('login'))
    admins = User.query.filter_by(tipo='admin').all()
    cooperados = User.query.filter_by(tipo='cooperado').all()
    tipos = TipoLancamento.query.all()
    valores = Valor.query.order_by(Valor.data.desc()).all()
    return render_template(
        "painel_master.html",
        admins=admins, cooperados=cooperados, tipos=tipos, valores=valores,
        dias_label=dias_label
    )

# --- Painel ADMIN ---
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

# --- Painel COOPERADO ---
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

# --- Cadastro Admin ---
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

# --- Cadastro Cooperado ---
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

# --- Cadastro de Tipo de Lançamento (Contrato) ---
@app.route("/cadastrar_tipo_lancamento", methods=["POST"])
@login_required
def cadastrar_tipo_lancamento():
    if current_user.tipo != 'master':
        return redirect(url_for('login'))
    nome = request.form['nome']
    tipo = request.form['tipo']
    if TipoLancamento.query.filter_by(nome=nome, tipo=tipo).first():
        flash("Tipo já cadastrado!", "danger")
    else:
        novo_tipo = TipoLancamento(nome=nome, tipo=tipo)
        db.session.add(novo_tipo)
        db.session.commit()
        flash("Tipo de lançamento cadastrado!", "success")
    return redirect(url_for('painel_master'))

# --- Exclusão de Tipo de Lançamento ---
@app.route("/excluir_tipo_lancamento/<int:tipo_id>", methods=["POST"])
@login_required
def excluir_tipo_lancamento(tipo_id):
    if current_user.tipo != 'master':
        return redirect(url_for('login'))
    tipo = TipoLancamento.query.get(tipo_id)
    if tipo:
        db.session.delete(tipo)
        db.session.commit()
        flash("Contrato excluído!", "success")
    return redirect(url_for('painel_master'))

# --- Cadastro Valor/Desconto ---
@app.route("/cadastro_valor", methods=["GET", "POST"])
@login_required
def cadastro_valor():
    if current_user.tipo not in ['master', 'admin']:
        return redirect(url_for('login'))
    cooperados = User.query.filter_by(tipo='cooperado').all()
    tipos = TipoLancamento.query.all()
    if request.method == "POST":
        cooperado_id = request.form["cooperado_id"]
        tipo_lancamento_id = request.form.get("tipo_lancamento_id")
        data_str = request.form["data"]
        turno = request.form["turno"]
        tipo = request.form["tipo"]
        valor_br = request.form["valor"]
        valor_num = float(valor_br.replace('R$', '').replace('.', '').replace(',', '.').strip())
        try:
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
        except:
            flash("Data inválida!", "danger")
            return render_template("cadastro_valor.html", cooperados=cooperados, tipos=tipos, now=datetime.now)
        novo = Valor(
            cooperado_id=cooperado_id,
            tipo_lancamento_id=tipo_lancamento_id,
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
    return render_template("cadastro_valor.html", cooperados=cooperados, tipos=tipos, now=datetime.now)

# --- Exclusão Admin/Cooperado/Valor ---
@app.route("/excluir_admin/<int:admin_id>", methods=["POST"])
@login_required
def excluir_admin(admin_id):
    if current_user.tipo != 'master':
        return redirect(url_for('login'))
    admin = User.query.get(admin_id)
    if admin:
        db.session.delete(admin)
        db.session.commit()
        flash("Admin excluído!", "success")
    return redirect(url_for('painel_master'))

@app.route("/excluir_cooperado/<int:cooperado_id>", methods=["POST"])
@login_required
def excluir_cooperado(cooperado_id):
    if current_user.tipo != 'master':
        return redirect(url_for('login'))
    c = User.query.get(cooperado_id)
    if c:
        db.session.delete(c)
        db.session.commit()
        flash("Cooperado excluído!", "success")
    return redirect(url_for('painel_master'))

@app.route("/excluir_valor/<int:valor_id>", methods=["POST"])
@login_required
def excluir_valor(valor_id):
    v = Valor.query.get(valor_id)
    if v:
        db.session.delete(v)
        db.session.commit()
        flash("Lançamento excluído!", "success")
    if current_user.tipo == "master":
        return redirect(url_for('painel_master'))
    else:
        return redirect(url_for('painel_admin'))

# --- Editar Admin/Cooperado/Valor/Contrato ---
@app.route("/editar_admin/<int:admin_id>", methods=["GET", "POST"])
@login_required
def editar_admin(admin_id):
    if current_user.tipo != 'master':
        return redirect(url_for('login'))
    admin = User.query.get(admin_id)
    if not admin or admin.tipo != "admin":
        return redirect(url_for('painel_master'))
    if request.method == "POST":
        admin.nome = request.form["nome"]
        admin.username = request.form["username"]
        admin.intervalo_inicio = request.form["intervalo_inicio"]
        admin.intervalo_fim = request.form["intervalo_fim"]
        senha = request.form["senha"]
        if senha:
            admin.set_password(senha)
        db.session.commit()
        flash("Admin atualizado!", "success")
        return redirect(url_for('painel_master'))
    return render_template("editar_admin.html", admin=admin, dias=dias, dias_label=dias_label)

@app.route("/editar_cooperado/<int:cooperado_id>", methods=["GET", "POST"])
@login_required
def editar_cooperado(cooperado_id):
    if current_user.tipo != 'master':
        return redirect(url_for('login'))
    cooperado = User.query.get(cooperado_id)
    if not cooperado or cooperado.tipo != "cooperado":
        return redirect(url_for('painel_master'))
    if request.method == "POST":
        cooperado.nome = request.form["nome"]
        cooperado.username = request.form["username"]
        senha = request.form["senha"]
        if senha:
            cooperado.set_password(senha)
        db.session.commit()
        flash("Cooperado atualizado!", "success")
        return redirect(url_for('painel_master'))
    return render_template("editar_cooperado.html", cooperado=cooperado)

@app.route("/editar_valor/<int:valor_id>", methods=["GET", "POST"])
@login_required
def editar_valor(valor_id):
    valor = Valor.query.get(valor_id)
    cooperados = User.query.filter_by(tipo='cooperado').all()
    tipos = TipoLancamento.query.all()
    if request.method == "POST":
        valor.cooperado_id = request.form["cooperado_id"]
        valor.tipo_lancamento_id = request.form.get("tipo_lancamento_id")
        valor.data = datetime.strptime(request.form["data"], '%Y-%m-%d').date()
        valor.turno = request.form["turno"]
        valor.tipo = request.form["tipo"]
        valor.valor = float(request.form["valor"].replace('R$', '').replace('.', '').replace(',', '.').strip())
        db.session.commit()
        flash("Lançamento atualizado!", "success")
        if current_user.tipo == "master":
            return redirect(url_for('painel_master'))
        else:
            return redirect(url_for('painel_admin'))
    return render_template("editar_valor.html", valor=valor, cooperados=cooperados, tipos=tipos, now=datetime.now)

@app.route("/editar_tipo_lancamento/<int:tipo_id>", methods=["GET", "POST"])
@login_required
def editar_tipo_lancamento(tipo_id):
    if current_user.tipo != 'master':
        return redirect(url_for('login'))
    tipo = TipoLancamento.query.get(tipo_id)
    if not tipo:
        return redirect(url_for('painel_master'))
    if request.method == "POST":
        tipo.nome = request.form["nome"]
        tipo.tipo = request.form["tipo"]
        db.session.commit()
        flash("Tipo de lançamento atualizado!", "success")
        return redirect(url_for('painel_master'))
    return render_template("editar_tipo_lancamento.html", tipo=tipo)

@app.errorhandler(401)
def unauthorized(e):
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
