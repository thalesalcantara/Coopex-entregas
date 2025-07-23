# criar_admin.py
from app import app
from models import db, Admin

with app.app_context():
    db.create_all()  # Cria as tabelas se não existirem
    usuario = Admin.query.filter_by(email='coopex').first()
    if usuario:
        print('Usuário admin já existe.')
    else:
        admin = Admin(nome='Coopex Master', email='coopex', tipo='master')
        admin.set_password('coopex05289')
        db.session.add(admin)
        db.session.commit()
        print('Usuário admin criado com sucesso!')
