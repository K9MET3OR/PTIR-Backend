from django.shortcuts import render
from django.db import IntegrityError
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Trip

# Create your views here.

def trip_para_json(trip):
    return {
        'id': str(trip.id),
        'client_id': str(trip.client_id),
        'driver_id': str(trip.driver_id),
        'taxi_id': str(trip.taxi_id),
        'shift_id': str(trip.shift_id),
        'data_inicio': trip.data_inicio,
        'data_fim': trip.data_fim,
        'local_inicio': trip.local_inicio,
        'local_fim': trip.local_fim,
        'n_pessoas': trip.n_pessoas,
        'n_kms': str(trip.n_kms) if trip.n_kms is not None else None,
        'preco': str(trip.preco) if trip.preco is not None else None,
        'status_viagem': trip.status_viagem,
    }


@api_view(['POST'])
def registar_trip(request):
    data = request.data

    campos_obrigatorios = [
        'client',
        'driver',
        'taxi',
        'shift',
        'data_inicio',
        'local_inicio',
        'local_fim',
        'n_pessoas',
    ]

    for campo in campos_obrigatorios:
        if campo not in data or str(data[campo]).strip() == '':
            return Response({'message': f'{campo} é obrigatório.'}, status=400)

    try:
        trip = Trip.objects.create(
            client_id=data['client'],
            driver_id=data['driver'],
            taxi_id=data['taxi'],
            shift_id=data['shift'],
            data_inicio=data['data_inicio'],
            data_fim=data.get('data_fim'),
            local_inicio=data['local_inicio'],
            local_fim=data['local_fim'],
            n_pessoas=data['n_pessoas'],
            n_kms=data.get('n_kms'),
            preco=data.get('preco'),
            status_viagem=data.get('status_viagem', 'pending'),
        )
    except IntegrityError:
        return Response({'message': 'Erro ao registar trip.'}, status=409)

    return Response(
        {
            'success': True,
            'trip': trip_para_json(trip),
        },
        status=201,
    )


@api_view(['GET'])
def listar_trips(request):
    trips = Trip.objects.all().order_by('-data_inicio')

    resultado = []
    for trip in trips:
        resultado.append(trip_para_json(trip))

    return Response(
        {
            'success': True,
            'trips': resultado,
            'total': len(resultado),
        },
        status=200,
    )


@api_view(['GET', 'PATCH', 'PUT', 'DELETE'])
def gerir_trip(request, id_trip):
    trip = Trip.objects.filter(pk=id_trip).first()

    if not trip:
        return Response({'message': 'Trip não encontrada.'}, status=404)

    if request.method == 'GET':
        return Response(
            {
                'success': True,
                'trip': trip_para_json(trip),
            },
            status=200,
        )

    if request.method == 'DELETE':
        trip_id = str(trip.id)
        trip.delete()

        return Response(
            {
                'success': True,
                'message': 'Trip apagada.',
                'id': trip_id,
            },
            status=200,
        )

    data = request.data

    if not data:
        return Response({'message': 'Nenhum campo para atualizar.'}, status=400)

    if 'client' in data:
        trip.client_id = data['client']

    if 'driver' in data:
        trip.driver_id = data['driver']

    if 'taxi' in data:
        trip.taxi_id = data['taxi']

    if 'shift' in data:
        trip.shift_id = data['shift']

    if 'data_inicio' in data:
        trip.data_inicio = data['data_inicio']

    if 'data_fim' in data:
        trip.data_fim = data['data_fim']

    if 'local_inicio' in data:
        local_inicio = str(data['local_inicio']).strip()
        if local_inicio == '':
            return Response({'message': 'local_inicio é obrigatório.'}, status=400)
        trip.local_inicio = local_inicio

    if 'local_fim' in data:
        local_fim = str(data['local_fim']).strip()
        if local_fim == '':
            return Response({'message': 'local_fim é obrigatório.'}, status=400)
        trip.local_fim = local_fim

    if 'n_pessoas' in data:
        trip.n_pessoas = data['n_pessoas']

    if 'n_kms' in data:
        trip.n_kms = data['n_kms']

    if 'preco' in data:
        trip.preco = data['preco']

    if 'status_viagem' in data:
        trip.status_viagem = data['status_viagem']

    try:
        trip.save()
    except IntegrityError:
        return Response({'message': 'Erro ao atualizar trip.'}, status=409)

    return Response(
        {
            'success': True,
            'trip': trip_para_json(trip),
        },
        status=200,
    )


@api_view(['POST'])
def accept_trip(request, pk):
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response(status=404)

    if trip.status_viagem != "pending":
        return Response({"error": "Trip not available"}, status=400)

    trip.status_viagem = "accepted"
    trip.save()

    return Response({"message": "Trip accepted"})


@api_view(['POST'])
def finish_trip(request, pk):
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response(status=404)

    trip.status_viagem = "finished"
    trip.save()

    return Response({"message": "Trip finished"})