import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'sua-chave-secreta-aqui'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql+psycopg2://usuario:senha@localhost:5432/nome_do_banco'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
