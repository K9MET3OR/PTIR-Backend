from django.db import IntegrityError
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.user.utils import validar_nif

from .models import Admin
from .services import create_admin, login_admin
from .validators import validate_admin_payload


def admin_para_json(admin):
    return {
        'id': str(admin.id),
        'username': admin.username,
        'email': admin.email,
        'name': admin.name,
        'role': admin.role,
        'nif': admin.nif,
    }


@api_view(['POST'])
def registo_admin(request):
    data = request.data

    err = validate_admin_payload(data)
    if err:
        return Response({'message': err}, status=400)

    user, service_err, status_code = create_admin(data)
    if service_err:
        return Response({'message': service_err}, status=status_code)

    return Response(
        {
            'success': True,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'name': user.name,
                'role': user.role,
                'nif': user.nif,
            },
        },
        status=201,
    )


@api_view(['POST'])
def login_admin_nif(request):
    nif = str(request.data.get('nif', '')).strip()

    if not validar_nif(nif):
        return Response({'message': 'NIF invalido.'}, status=400)

    payload, service_err, status_code = login_admin(request.data)
    if service_err:
        return Response({'message': service_err}, status=status_code)

    return Response(payload, status=200)


@api_view(['GET'])
def listar_admins(request):
    admins = Admin.objects.all().order_by('name')

    resultado = []
    for admin in admins:
        resultado.append(admin_para_json(admin))

    return Response(
        {
            'success': True,
            'admins': resultado,
            'total': len(resultado),
        },
        status=200,
    )


@api_view(['GET', 'PATCH', 'PUT', 'DELETE'])
def gerir_admin(request, id_admin):
    admin = Admin.objects.filter(pk=id_admin).first()

    if not admin:
        return Response({'message': 'Admin nao encontrado.'}, status=404)

    if request.method == 'GET':
        return Response(
            {
                'success': True,
                'admin': admin_para_json(admin),
            },
            status=200,
        )

    if request.method == 'DELETE':
        admin_id = str(admin.id)
        admin.delete()

        return Response(
            {
                'success': True,
                'message': 'Admin apagado.',
                'id': admin_id,
            },
            status=200,
        )

    data = request.data

    if not data:
        return Response({'message': 'Nenhum campo para atualizar.'}, status=400)

    if 'username' in data:
        username = str(data['username']).strip()
        if username == '':
            return Response({'message': 'username e obrigatorio.'}, status=400)

        existe = Admin.objects.filter(username=username).exclude(pk=admin.pk).exists()
        if existe:
            return Response({'message': 'Username ja existe.'}, status=409)

        admin.username = username

    if 'email' in data:
        email = str(data['email']).strip()
        if email == '':
            return Response({'message': 'email e obrigatorio.'}, status=400)

        existe = Admin.objects.filter(email=email).exclude(pk=admin.pk).exists()
        if existe:
            return Response({'message': 'Email ja registado.'}, status=409)

        admin.email = email

    if 'name' in data:
        name = str(data['name']).strip()
        if name == '':
            return Response({'message': 'name e obrigatorio.'}, status=400)

        admin.name = name

    if 'nif' in data:
        nif = str(data['nif']).strip()
        if not validar_nif(nif):
            return Response({'message': 'NIF invalido.'}, status=400)

        existe = Admin.objects.filter(nif=nif).exclude(pk=admin.pk).exists()
        if existe:
            return Response({'message': 'NIF ja registado.'}, status=409)

        admin.nif = nif

    try:
        admin.save()
    except IntegrityError:
        return Response({'message': 'Erro ao atualizar admin.'}, status=409)

    return Response(
        {
            'success': True,
            'admin': admin_para_json(admin),
        },
        status=200,
    )