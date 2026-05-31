from django.db import IntegrityError
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.user.utils import validar_nif

from .models import Client
from .services import create_client, login_client
from .validators import validate_client_payload


def client_para_json(client):
    return {
        'id': str(client.id),
        'username': client.username,
        'email': client.email,
        'name': client.name,
        'role': client.role,
        'nif': client.nif,
        'genero': client.genero,
    }


@api_view(['POST'])
def registo_client(request):
    data = request.data

    err = validate_client_payload(data)
    if err:
        return Response({'message': err}, status=400)

    client, service_err, status_code = create_client(data)
    if service_err:
        return Response({'message': service_err}, status=status_code)

    return Response(
        {
            'success': True,
            'user': client_para_json(client),
        },
        status=201,
    )


@api_view(['POST'])
def login_client_nif(request):
    nif = str(request.data.get('nif', '')).strip()

    if not validar_nif(nif):
        return Response({'message': 'NIF inválido.'}, status=400)

    payload, service_err, status_code = login_client(request.data)
    if service_err:
        return Response({'message': service_err}, status=status_code)

    return Response(payload, status=200)


@api_view(['GET'])
def listar_clients(request):
    clients = Client.objects.all().order_by('name')

    resultado = []
    for client in clients:
        resultado.append(client_para_json(client))

    return Response(
        {
            'success': True,
            'clients': resultado,
            'total': len(resultado),
        },
        status=200,
    )


@api_view(['GET', 'PATCH', 'PUT', 'DELETE'])
def gerir_client(request, id_client):
    client = Client.objects.filter(pk=id_client).first()

    if not client:
        return Response({'message': 'Client não encontrado.'}, status=404)

    if request.method == 'GET':
        return Response(
            {
                'success': True,
                'client': client_para_json(client),
            },
            status=200,
        )

    if request.method == 'DELETE':
        client_id = str(client.id)
        client.delete()

        return Response(
            {
                'success': True,
                'message': 'Client apagado.',
                'id': client_id,
            },
            status=200,
        )

    data = request.data

    if not data:
        return Response({'message': 'Nenhum campo para atualizar.'}, status=400)

    if 'username' in data:
        username = str(data['username']).strip()
        if username == '':
            return Response({'message': 'username é obrigatório.'}, status=400)

        existe = Client.objects.filter(username=username).exclude(pk=client.pk).exists()
        if existe:
            return Response({'message': 'Username já existe.'}, status=409)

        client.username = username

    if 'email' in data:
        email = str(data['email']).strip()
        if email == '':
            return Response({'message': 'email é obrigatório.'}, status=400)

        existe = Client.objects.filter(email=email).exclude(pk=client.pk).exists()
        if existe:
            return Response({'message': 'Email já registado.'}, status=409)

        client.email = email

    if 'name' in data:
        name = str(data['name']).strip()
        if name == '':
            return Response({'message': 'name é obrigatório.'}, status=400)

        client.name = name

    if 'nif' in data:
        nif = str(data['nif']).strip()
        if not validar_nif(nif):
            return Response({'message': 'NIF inválido.'}, status=400)

        existe = Client.objects.filter(nif=nif).exclude(pk=client.pk).exists()
        if existe:
            return Response({'message': 'NIF já registado.'}, status=409)

        client.nif = nif

    if 'genero' in data:
        genero = str(data['genero']).strip().lower()
        if genero not in ('feminino', 'masculino'):
            return Response(
                {'message': "Genero invalido. Deve ser 'feminino' ou 'masculino'."},
                status=400
            )

        client.genero = genero

    try:
        client.save()
    except IntegrityError:
        return Response({'message': 'Erro ao atualizar client.'}, status=409)

    return Response(
        {
            'success': True,
            'client': client_para_json(client),
        },
        status=200,
    )