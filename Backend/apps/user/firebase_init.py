import firebase_admin
from firebase_admin import credentials
import os

# Inicializar Firebase Admin SDK apenas uma vez
try:
    firebase_admin.get_app()
except ValueError:
    # App não existe, criar
    cred_path = os.path.join(os.path.dirname(__file__), '../../firebase-adminsdk.json')
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
