from rest_framework.decorators import api_view
from rest_framework.response import Response
from functools import wraps

from .models import User

import bcrypt
from firebase_admin import auth


# Auth decorator 

def firebase_auth_required(f):
    """
    Verifica o token Firebase no header Authorization.
    Injeta `firebase_uid` e `firebase_email` no request.
    """
    @wraps(f)
    def decorated(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return Response({'message': 'Token em falta'}, status=401)

        token = auth_header.split(' ')[1]
        try:
            decoded = auth.verify_id_token(token)
        except auth.ExpiredIdTokenError:
            return Response({'message': 'Token expirado'}, status=401)
        except Exception:
            return Response({'message': 'Token inválido'}, status=401)

        request.firebase_uid   = decoded['uid']
        request.firebase_email = decoded.get('email', '')
        return f(request, *args, **kwargs)
    return decorated


def get_user_from_request(request):
    """
    Resolve o utilizador Django a partir do uid/email Firebase.
    Retorna (user, error_response). Um dos dois será None.
    """
    uid   = request.firebase_uid
    email = request.firebase_email

    user = User.objects.filter(uid=uid).first()
    if user:
        return user, None

    user = User.objects.filter(email=email).first()
    if user:
        user.uid = uid
        user.save(update_fields=['uid'])
        return user, None

    return None, Response({'message': 'Utilizador não encontrado'}, status=404)


# CREATE USER  (RF-01, RF-02, RF-03)


@api_view(['POST'])
@firebase_auth_required
def create_user(request):
    data = request.data

    username = data.get('username', '').strip()
    name     = data.get('name', '').strip()
    role     = data.get('role', 'cliente')
    mobile   = data.get('mobile', '')
    address  = data.get('address', '')

    email = request.firebase_email
    uid   = request.firebase_uid

    if not username or not name:
        return Response({'message': 'username e name são obrigatórios'}, status=400)

    if role not in ('cliente', 'motorista', 'gestor'):
        return Response({'message': 'Role inválida'}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({'message': 'Username já existe'}, status=409)

    if User.objects.filter(email=email).exists():
        return Response({'message': 'Email já registado'}, status=409)

    user = User.objects.create(
        uid      = uid,
        username = username,
        email    = email,
        name     = name,
        role     = role,
        mobile   = mobile,
        address  = address,
    )

    return Response({
        'success': True,
        'user': {
            'id':       str(user.id),
            'username': user.username,
            'email':    user.email,
            'role':     user.role,
        }
    }, status=201)


# LOGIN  (RF-05)

@api_view(['POST'])
@firebase_auth_required
def login(request):
    selected_role = request.data.get('selectedRole')
    if not selected_role:
        return Response({'message': 'selectedRole é obrigatório'}, status=400)

    user, err = get_user_from_request(request)
    if err:
        return err

    if user.role != selected_role:
        return Response({'message': 'Role incorreta para este utilizador'}, status=403)

    return Response({
        'success': True,
        'user': {
            'id':       str(user.id),
            'username': user.username,
            'name':     user.name,
            'role':     user.role,
        }
    })

# GET USER  (RF-01, RF-02, RF-03)

@api_view(['GET'])
@firebase_auth_required
def get_user(request, id):
    user, err = get_user_from_request(request)
    if err:
        return err

    # O utilizador só pode ver o seu próprio perfil, ou o gestor pode ver todos
    if str(user.id) != id and user.role != 'gestor':
        return Response({'message': 'Não autorizado'}, status=403)

    try:
        target = User.objects.get(id=id)
    except User.DoesNotExist:
        return Response({'message': 'Utilizador não encontrado'}, status=404)

    return Response({
        'id':       str(target.id),
        'username': target.username,
        'name':     target.name,
        'email':    target.email,
        'role':     target.role,
        'mobile':   target.mobile,
        'address':  target.address,
    })


# UPDATE USER  (RF-01, RF-02, RF-03)


@api_view(['PATCH'])
@firebase_auth_required
def update_user(request, id):
    user, err = get_user_from_request(request)
    if err:
        return err

    if str(user.id) != id and user.role != 'gestor':
        return Response({'message': 'Não autorizado'}, status=403)

    try:
        target = User.objects.get(id=id)
    except User.DoesNotExist:
        return Response({'message': 'Utilizador não encontrado'}, status=404)

    editable_fields = ('name', 'mobile', 'address')
    updated = []

    for field in editable_fields:
        if field in request.data:
            setattr(target, field, request.data[field])
            updated.append(field)

    if 'role' in request.data:
        if user.role != 'gestor':
            return Response({'message': 'Sem permissão para alterar role'}, status=403)
        if request.data['role'] not in ('cliente', 'motorista', 'gestor'):
            return Response({'message': 'Role inválida'}, status=400)
        target.role = request.data['role']
        updated.append('role')

    if not updated:
        return Response({'message': 'Nenhum campo válido para atualizar'}, status=400)

    target.save(update_fields=updated)

    return Response({'success': True, 'updated_fields': updated})



# DELETE USER  (RF-01, RF-02, RF-03)


@api_view(['DELETE'])
@firebase_auth_required
def delete_user(request, id):
    user, err = get_user_from_request(request)
    if err:
        return err

    if str(user.id) != id and user.role != 'gestor':
        return Response({'message': 'Não autorizado'}, status=403)

    try:
        target = User.objects.get(id=id)
    except User.DoesNotExist:
        return Response({'message': 'Utilizador não encontrado'}, status=404)

    if target.uid:
        try:
            auth.delete_user(target.uid)
        except Exception:
            pass  
    target.delete()
    return Response({'success': True})