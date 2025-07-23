from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, Admin, Cooperado, Valor, TipoLancamento

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    # Tenta carregar admin, se não for admin pode ser cooperado
    user = Admin.query.get(int(user_id))
    if user:
        return user
    return Cooperado.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        user = Admin.query.filter_by(email=email).first()
        if not user:
            user = Cooperado.query.filter_by(email=email).first()
        if user and user.check_password(senha):
            login_user(user)
            flash('Login realizado com sucesso!', 'success')
            if isinstance(user, Admin):
                return redirect(url_for('painel_admin'))
            else:
                return redirect(url_for('painel_cooperado'))
        else:
            flash('Login ou senha incorretos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# PAINEL ADMIN
@app.route('/painel_admin')
@login_required
def painel_admin():
    if not isinstance(current_user, Admin):
        return redirect(url_for('painel_cooperado'))
    admins = Admin.query.all()
    cooperados = Cooperado.query.all()
    valores = Valor.query.all()
    tipos = TipoLancamento.query.all()
    return render_template('admin.html',
                           admins=admins,
                           cooperados=cooperados,
                           valores=valores,
                           tipos=tipos)

# PAINEL COOPERADO
@app.route('/painel_cooperado')
@login_required
def painel_cooperado():
    if not isinstance(current_user, Cooperado):
        return redirect(url_for('painel_admin'))
    valores = Valor.query.filter_by(cooperado_id=current_user.id).all()
    return render_template('cooperado.html', valores=valores)

# CADASTRAR COOPERADO (apenas admin master)
@app.route('/cadastrar_cooperado', methods=['GET', 'POST'])
@login_required
def cadastrar_cooperado():
    if not isinstance(current_user, Admin) or current_user.tipo != 'master':
        return redirect(url_for('painel_admin'))
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        if Cooperado.query.filter_by(email=email).first():
            flash('E-mail já cadastrado para cooperado!', 'danger')
        else:
            novo = Cooperado(nome=nome, email=email)
            novo.set_password(senha)
            db.session.add(novo)
            db.session.commit()
            flash('Cooperado cadastrado com sucesso!', 'success')
            return redirect(url_for('painel_admin'))
    return render_template('cadastrar_cooperado.html')

# CADASTRAR ENTREGA/VALOR
@app.route('/cadastrar_entrega', methods=['GET', 'POST'])
@login_required
def cadastrar_entrega():
    if not isinstance(current_user, Admin):
        return redirect(url_for('painel_cooperado'))
    cooperados = Cooperado.query.all()
    tipos = TipoLancamento.query.all()
    if request.method == 'POST':
        cooperado_id = request.form.get('cooperado_id')
        tipo_lancamento_id = request.form.get('tipo_lancamento_id')
        valor = request.form.get('valor')
        data = request.form.get('data')
        novo = Valor(
            cooperado_id=cooperado_id,
            tipo_lancamento_id=tipo_lancamento_id,
            valor=float(valor),
            data=data
        )
        db.session.add(novo)
        db.session.commit()
        flash('Entrega/valor cadastrada com sucesso!', 'success')
        return redirect(url_for('painel_admin'))
    return render_template('cadastrar_entrega.html', cooperados=cooperados, tipos=tipos)

# EDITAR ENTREGA/VALOR
@app.route('/editar_entrega/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_entrega(id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('painel_cooperado'))
    entrega = Valor.query.get_or_404(id)
    cooperados = Cooperado.query.all()
    tipos = TipoLancamento.query.all()
    if request.method == 'POST':
        entrega.cooperado_id = request.form.get('cooperado_id')
        entrega.tipo_lancamento_id = request.form.get('tipo_lancamento_id')
        entrega.valor = float(request.form.get('valor'))
        entrega.data = request.form.get('data')
        db.session.commit()
        flash('Entrega editada com sucesso!', 'success')
        return redirect(url_for('painel_admin'))
    return render_template('editar_entrega.html', entrega=entrega, cooperados=cooperados, tipos=tipos)

# ESTATÍSTICAS
@app.route('/estatisticas')
@login_required
def estatisticas():
    if not isinstance(current_user, Admin):
        return redirect(url_for('painel_cooperado'))
    valores = Valor.query.all()
    return render_template('estatisticas.html', valores=valores)

# CRIAÇÃO DE TIPO DE LANÇAMENTO (caso não exista)
@app.route('/cadastrar_tipo_lancamento', methods=['GET', 'POST'])
@login_required
def cadastrar_tipo_lancamento():
    if not isinstance(current_user, Admin):
        return redirect(url_for('painel_cooperado'))
    if request.method == 'POST':
        nome = request.form.get('nome')
        if TipoLancamento.query.filter_by(nome=nome).first():
            flash('Tipo já existe!', 'danger')
        else:
            tipo = TipoLancamento(nome=nome)
            db.session.add(tipo)
            db.session.commit()
            flash('Tipo de lançamento cadastrado!', 'success')
            return redirect(url_for('cadastrar_entrega'))
    return render_template('cadastrar_tipo_lancamento.html')

if __name__ == "__main__":
    app.run(debug=True)
