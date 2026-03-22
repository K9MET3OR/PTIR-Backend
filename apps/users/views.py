
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import User

import bcrypt
import jwt
import datetime
from django.conf import settings


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

    # validação básica
    if not username or not email or not password or not name:
        return Response({'message': 'Campos obrigatórios em falta'}, status=400)

    # verificar duplicados
    if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
        return Response({'message': 'Username ou email já existe'}, status=409)

    # hash password
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    user = User.objects.create(
        username=username.strip(),
        email=email.lower().strip(),
        password=hashed.decode('utf-8'),
        name=name,
        mobile=mobile,
        address=address
    )

    return Response({
        'success': True,
        'user': {
            'id': str(user.id),
            'username': user.username,
            'email': user.email
        }
    }, status=201)


# LOGIN
@api_view(['POST'])
def login(request):
    data = request.data

    identifier = data.get('identifier')
    password = data.get('password')

    try:
        user = User.objects.get(email=identifier)
    except:
        try:
            user = User.objects.get(username=identifier)
        except:
            return Response({'message': 'Credenciais inválidas'}, status=401)

    if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return Response({'message': 'Credenciais inválidas'}, status=401)

    payload = {
        'id': str(user.id),
        'username': user.username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    return Response({
        'success': True,
        'token': token,
        'user': {
            'id': str(user.id),
            'username': user.username,
            'name': user.name
        }
    })


# DELETE USER
@api_view(['DELETE'])
def delete_user(request, id):

    auth_header = request.headers.get('Authorization')

    if not auth_header:
        return Response({'message': 'Sem token'}, status=401)

    try:
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    except:
        return Response({'message': 'Token inválido'}, status=401)

    if str(payload['id']) != id:
        return Response({'message': 'Não autorizado'}, status=403)

    try:
        user = User.objects.get(id=id)
        user.delete()
        return Response({'success': True})
    except:
        return Response({'message': 'User não encontrado'}, status=404)