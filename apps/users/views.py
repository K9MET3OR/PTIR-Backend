from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import User

import bcrypt
import jwt
import datetime
from django.conf import settings

import firebase_admin
from firebase_admin import auth, credentials

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    import os
    if os.path.exists('firebase-adminsdk.json'):
        cred = credentials.Certificate('firebase-adminsdk.json')
        firebase_admin.initialize_app(cred)
    else:
        # For development, you can use default credentials if running on GCP
        # or set GOOGLE_APPLICATION_CREDENTIALS environment variable
        firebase_admin.initialize_app()


# CREATE USER
@api_view(['POST'])
def create_user(request):
    data = request.data

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    mobile = data.get('mobile')
    address = data.get('address')
    role = data.get('role', 'cliente')

    if not username or not email or not name:
        return Response({'message': 'Campos obrigatórios em falta'}, status=400)

    if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
        return Response({'message': 'Username ou email já existe'}, status=409)
    
    hashed = None
    if password:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    user = User.objects.create(
        username=username.strip(),
        email=email.lower().strip(),
        password=hashed,
        name=name,
        role=role,
        mobile=mobile,
        address=address
    )

    return Response({
        'success': True,
        'user': {
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'role': user.role
        }
    }, status=201)


# LOGIN
@api_view(['POST'])
def login(request):
    data = request.data
    selectedRole = data.get('selectedRole')

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return Response({'message': 'Sem token'}, status=401)

    token = auth_header.split(' ')[1]
    try:
        decoded_token = auth.verify_id_token(token)
    except:
        return Response({'message': 'Token inválido'}, status=401)

    uid = decoded_token['uid']
    email = decoded_token['email']

    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        try:
            user = User.objects.get(email=email)
            user.uid = uid
            user.save()
        except User.DoesNotExist:
            return Response({'message': 'User não encontrado'}, status=404)

    if user.role != selectedRole:
        return Response({'message': 'Role inválida'}, status=403)

    payload = {
        'id': str(user.id),
        'username': user.username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }

    django_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    return Response({
        'success': True,
        'token': token,  # Return Firebase token
        'user': {
            'id': str(user.id),
            'username': user.username,
            'name': user.name,
            'role': user.role
        }
    })


# DELETE USER
@api_view(['DELETE'])
def delete_user(request, id):

    auth_header = request.headers.get('Authorization')

    if not auth_header or not auth_header.startswith('Bearer '):
        return Response({'message': 'Sem token'}, status=401)

    token = auth_header.split(' ')[1]
    try:
        decoded_token = auth.verify_id_token(token)
    except:
        return Response({'message': 'Token inválido'}, status=401)

    uid = decoded_token['uid']
    try:
        user = User.objects.get(uid=uid)
    except:
        return Response({'message': 'User não encontrado'}, status=404)

    if str(user.id) != id:
        return Response({'message': 'Não autorizado'}, status=403)

    user.delete()
    return Response({'success': True})