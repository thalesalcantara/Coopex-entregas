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
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # "valor" ou "desconto"

class Valor(db.Model):
    __tablename__ = 'valores'
    id = db.Column(db.Integer, primary_key=True)
    cooperado_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)
    turno = db.Column(db.String(30), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # valor ou desconto
    criado_por = db.Column(db.Integer, db.ForeignKey('users.id'))
    tipo_lancamento_id = db.Column(db.Integer, db.ForeignKey('tipos_lancamento.id'), nullable=False)

    cooperado = db.relationship('User', foreign_keys=[cooperado_id])
    criador = db.relationship('User', foreign_keys=[criado_por])
    tipo_lancamento = db.relationship('TipoLancamento')

# --- LOGIN MANAGER ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- CRIA TABELAS E USUÁRIO MASTER SE NÃO EXISTIREM ---
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
    return render_template("login.html", ano=datetime.now().year)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# PAINEL MASTER
@app.route("/painel_master", methods=["GET", "POST"])
@login_required
def painel_master():
    if current_user.tipo != 'master':
        return redirect(url_for('login'))
    admins = User.query.filter_by(tipo='admin').all()
    cooperados = User.query.filter_by(tipo='cooperado').all()
    valores = Valor.query.order_by(Valor.data.desc()).all()
    tipos_valor = TipoLancamento.query.filter_by(tipo="valor").all()
    tipos_desconto = TipoLancamento.query.filter_by(tipo="desconto").all()
    tipos = TipoLancamento.query.order_by(TipoLancamento.tipo, TipoLancamento.nome).all()
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
        dias_label=dias_label,
        tipos_valor=tipos_valor,
        tipos_desconto=tipos_desconto,
        tipos=tipos
    )

@app.route("/cadastro_valor", methods=["GET", "POST"])
@login_required
def cadastro_valor():
    if current_user.tipo not in ['master', 'admin']:
        return redirect(url_for('login'))
    cooperados = User.query.filter_by(tipo='cooperado').all()
    tipos_valor = TipoLancamento.query.filter_by(tipo="valor").all()
    tipos_desconto = TipoLancamento.query.filter_by(tipo="desconto").all()
    if request.method == "POST":
        cooperado_id = request.form["cooperado_id"]
        data_str = request.form["data"]
        turno = request.form["turno"]
        tipo = request.form["tipo"]
        if tipo == "valor":
            tipo_lancamento_id = request.form.get("tipo_lancamento_valor")
        else:
            tipo_lancamento_id = request.form.get("tipo_lancamento_desconto")
        valor_br = request.form["valor"]
        valor_num = float(valor_br.replace('R$', '').replace('.', '').replace(',', '.').strip())
        try:
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
        except:
            flash("Data inválida!", "danger")
            return render_template("cadastro_valor.html", cooperados=cooperados, now=datetime.now, tipos_valor=tipos_valor, tipos_desconto=tipos_desconto)
        novo = Valor(
            cooperado_id=cooperado_id,
            valor=valor_num,
            data=data,
            turno=turno,
            tipo=tipo,
            criado_por=current_user.id,
            tipo_lancamento_id=tipo_lancamento_id
        )
        db.session.add(novo)
        db.session.commit()
        flash("Lançamento salvo com sucesso!", "success")
        if current_user.tipo == 'admin':
            return redirect(url_for('painel_admin'))
        else:
            return redirect(url_for('painel_master'))
    return render_template("cadastro_valor.html", cooperados=cooperados, now=datetime.now, tipos_valor=tipos_valor, tipos_desconto=tipos_desconto)

# EDITAR VALOR (ambos)
@app.route("/editar_valor/<int:valor_id>", methods=["GET", "POST"])
@login_required
def editar_valor(valor_id):
    if current_user.tipo not in ['master', 'admin']:
        return redirect(url_for('login'))
    valor = Valor.query.get_or_404(valor_id)
    cooperados = User.query.filter_by(tipo='cooperado').all()
    tipos_valor = TipoLancamento.query.filter_by(tipo="valor").all()
    tipos_desconto = TipoLancamento.query.filter_by(tipo="desconto").all()
    if request.method == "POST":
        valor.cooperado_id = request.form["cooperado_id"]
        valor.data = datetime.strptime(request.form["data"], '%Y-%m-%d').date()
        valor.turno = request.form["turno"]
        valor.tipo = request.form["tipo"]
        if valor.tipo == "valor":
            valor.tipo_lancamento_id = request.form.get("tipo_lancamento_valor")
        else:
            valor.tipo_lancamento_id = request.form.get("tipo_lancamento_desconto")
        valor.valor = float(request.form["valor"].replace('R$', '').replace('.', '').replace(',', '.').strip())
        db.session.commit()
        flash("Lançamento editado com sucesso!", "success")
        if current_user.tipo == 'admin':
            return redirect(url_for('painel_admin'))
        else:
            return redirect(url_for('painel_master'))
    return render_template("editar_valor.html", valor=valor, cooperados=cooperados, tipos_valor=tipos_valor, tipos_desconto=tipos_desconto)

# EXCLUIR VALOR (ambos)
@app.route('/excluir_valor/<int:valor_id>', methods=['POST'])
@login_required
def excluir_valor(valor_id):
    if current_user.tipo not in ['master', 'admin']:
        return redirect(url_for('login'))
    valor = Valor.query.get_or_404(valor_id)
    db.session.delete(valor)
    db.session.commit()
    flash("Lançamento excluído!", "success")
    if current_user.tipo == 'admin':
        return redirect(url_for('painel_admin'))
    else:
        return redirect(url_for('painel_master'))

# Rotas de contratos e cooperados (editar/excluir) — só master!
@app.route("/editar_cooperado/<int:cooperado_id>", methods=["GET", "POST"])
@login_required
def editar_cooperado(cooperado_id):
    if current_user.tipo != 'master':
        flash("Só o master pode editar cooperado.", "danger")
        return redirect(url_for('painel_master'))
    cooperado = User.query.get_or_404(cooperado_id)
    if request.method == "POST":
        cooperado.nome = request.form["nome"]
        cooperado.username = request.form["username"]
        if request.form["senha"]:
            cooperado.set_password(request.form["senha"])
        db.session.commit()
        flash("Cooperado editado!", "success")
        return redirect(url_for('painel_master'))
    return render_template("editar_cooperado.html", cooperado=cooperado)

@app.route('/excluir_cooperado/<int:cooperado_id>', methods=['POST'])
@login_required
def excluir_cooperado(cooperado_id):
    if current_user.tipo != 'master':
        flash("Só o master pode excluir cooperado.", "danger")
        return redirect(url_for('painel_master'))
    cooperado = User.query.get_or_404(cooperado_id)
    db.session.delete(cooperado)
    db.session.commit()
    flash("Cooperado excluído!", "success")
    return redirect(url_for('painel_master'))

@app.route('/excluir_admin/<int:admin_id>', methods=['POST'])
@login_required
def excluir_admin(admin_id):
    if current_user.tipo != 'master':
        flash("Apenas o master pode excluir admins.", "danger")
        return redirect(url_for('painel_master'))
    admin = User.query.get(admin_id)
    if admin and admin.tipo == 'admin':
        db.session.delete(admin)
        db.session.commit()
        flash('Admin excluído com sucesso!', 'success')
    else:
        flash('Admin não encontrado.', 'danger')
    return redirect(url_for('painel_master'))

@app.route('/excluir_tipo_lancamento/<int:tipo_id>', methods=['POST'])
@login_required
def excluir_tipo_lancamento(tipo_id):
    if current_user.tipo != 'master':
        flash("Só o master pode excluir contratos!", "danger")
        return redirect(url_for('painel_master'))
    tipo = TipoLancamento.query.get(tipo_id)
    if tipo:
        db.session.delete(tipo)
        db.session.commit()
        flash('Contrato excluído!', 'success')
    else:
        flash('Contrato não encontrado.', 'danger')
    return redirect(url_for('painel_master'))

@app.route("/cadastrar_tipo_lancamento", methods=["POST"])
@login_required
def cadastrar_tipo_lancamento():
    if current_user.tipo not in ['master', 'admin']:
        return redirect(url_for('login'))
    nome = request.form["nome"]
    tipo = request.form["tipo"]
    if TipoLancamento.query.filter_by(nome=nome, tipo=tipo).first():
        flash("Já existe um lançamento com esse nome/tipo!", "danger")
    else:
        novo = TipoLancamento(nome=nome, tipo=tipo)
        db.session.add(novo)
        db.session.commit()
        flash("Tipo cadastrado!", "success")
    return redirect(url_for('painel_master'))

# --- MAIN ---
if __name__ == '__main__':
    app.run(debug=True)
