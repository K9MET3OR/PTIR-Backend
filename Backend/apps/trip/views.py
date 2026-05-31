from django.shortcuts import render
from django.db import IntegrityError, connection
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Trip
import stripe
from django.utils import timezone
from apps.user.models import User
from apps.user.client.models import Client
from django.utils.dateparse import parse_datetime
from apps.user.views import firebase_auth_required, get_user_from_request
from apps.user.driver.models import Driver
from apps.shift.models import Shift

stripe.api_key = settings.STRIPE_SECRET_KEY if hasattr(settings, 'STRIPE_SECRET_KEY') else None

# Create your views here.

def trip_para_json(trip):
    # Obter nome do motorista se existir
    driver_name = None
    if trip.driver_id:
        try:
            # Driver herda de User, então pk é igual a user_id
            driver = Driver.objects.get(pk=trip.driver_id)
            # Obter o nome a partir do atributo 'name' do User
            driver_name = driver.name or "Motorista"
        except Exception as e:
            print(f"Erro ao obter driver: {e}")
            driver_name = "Motorista"
    
    # Obter matrícula do táxi se existir
    taxi_matricula = None
    taxi_id = trip.taxi_id
    
    print(f"[TRIP] Trip {trip.id}: taxi_id={taxi_id}, shift_id={trip.shift_id}")
    
    # Se o táxi não está diretamente atribuído, tentar obter do shift
    if not taxi_id and trip.shift_id:
        try:
            from apps.shift.models import Shift
            shift = Shift.objects.get(pk=trip.shift_id)
            taxi_id = shift.taxi_id
            print(f"[TRIP] Obtido taxi_id do shift: {taxi_id}")
        except Exception as e:
            print(f"Erro ao obter shift: {e}")
    
    if taxi_id:
        try:
            from apps.taxi.models import Taxi
            taxi = Taxi.objects.get(pk=taxi_id)
            taxi_matricula = taxi.matricula
            print(f"[TRIP] Obtida matrícula: {taxi_matricula}")
        except Exception as e:
            print(f"Erro ao obter taxi: {e}")
            taxi_matricula = "N/A"
    else:
        print(f"[TRIP] taxi_id é None")
        taxi_matricula = "N/A"
    
    return {
        'id': str(trip.id),
        'client_id': str(trip.client_id),
        'driver_id': str(trip.driver_id) if trip.driver_id else None,
        'driver_name': driver_name,
        'taxi_id': str(taxi_id) if taxi_id else None,
        'taxi_matricula': taxi_matricula,
        'shift_id': str(trip.shift_id) if trip.shift_id else None,
        'start_date': trip.start_date.isoformat() if trip.start_date else None,
        'end_date': trip.end_date.isoformat() if trip.end_date else None,
        'start_location': trip.start_location,
        'end_location': trip.end_location,
        'n_people': trip.n_people,
        'nivel_conforto': trip.nivel_conforto,
        'n_kms': str(trip.n_kms) if trip.n_kms is not None else None,
        'price': str(trip.price) if trip.price is not None else None,
        'status_trip': trip.status_trip,
        'created_at': trip.created_at.isoformat() if trip.created_at else None,
        'updated_at': trip.updated_at.isoformat() if trip.updated_at else None,
    }

@api_view(['POST'])
def registar_trip(request):
    data = request.data

    campos_obrigatorios = [
        'client_id',
        'start_location',
        'end_location',
        'n_people',
    ]

    # 1) Validar campos obrigat├│rios
    for campo in campos_obrigatorios:
        if campo not in data or str(data[campo]).strip() == '':
            return Response({'message': f'{campo} ├® obrigat├│rio.'}, status=400)

    # 2) Validar n├║mero de pessoas
    try:
        n_people = int(data['n_people'])
    except (TypeError, ValueError):
        return Response({'message': 'n_people inv├ílido.'}, status=400)

    if n_people < 1 or n_people > 4:
        return Response({'message': 'n_people deve estar entre 1 e 4.'}, status=400)

    # 3) Obter utilizador cliente
    try:
        user = User.objects.get(pk=data['client_id'], role='cliente')
    except User.DoesNotExist:
        return Response({'message': 'Cliente inv├ílido.'}, status=400)

    # 4) Garantir que existe registo na tabela Client
    client = Client.objects.filter(pk=user.pk).first()
    if not client:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO clients (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                [user.pk],
            )
        client = Client.objects.get(pk=user.pk)

    # 5) Tratar start_date
    start_date = data.get('start_date')
    if start_date:
        start_date = parse_datetime(start_date)
        if start_date is None:
            return Response({'message': 'start_date inv├ílida.'}, status=400)
    else:
        start_date = timezone.now()

    # 6) Criar viagem
    try:
        trip = Trip.objects.create(
            client=client,
            driver_id=data.get('driver_id'),
            taxi_id=data.get('taxi_id'),
            shift_id=data.get('shift_id'),
            start_date=start_date,
            end_date=data.get('end_date'),
            start_location=data['start_location'],
            end_location=data['end_location'],
            n_people=n_people,
            n_kms=data.get('n_kms'),
            price=data.get('price'),
            nivel_conforto=data.get('nivel_conforto', 'Standard'),
            status_trip=data.get('status_trip', 'pending'),
        )
    except IntegrityError as e:
        return Response({'message': f'Erro ao registar trip: {str(e)}'}, status=409)
    except Exception as e:
        return Response({'message': f'Erro: {str(e)}'}, status=400)

    return Response(
        {
            'success': True,
            'trip': trip_para_json(trip),
        },
        status=201,
    )


@api_view(['GET'])
def listar_trips(request):
    trips = Trip.objects.all().order_by('-start_date')

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
        return Response({'message': 'Trip n├úo encontrada.'}, status=404)

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

    if 'client_id' in data:
        trip.client_id = data['client_id']

    if 'driver_id' in data:
        trip.driver_id = data['driver_id']

    if 'taxi_id' in data:
        trip.taxi_id = data['taxi_id']

    if 'nivel_conforto' in data:
        trip.nivel_conforto = data['nivel_conforto']

    if 'shift_id' in data:
        trip.shift_id = data['shift_id']

    if 'start_date' in data:
        trip.start_date = data['start_date']

    if 'end_date' in data:
        trip.end_date = data['end_date']

    if 'start_location' in data:
        start_location = str(data['start_location']).strip()
        if start_location == '':
            return Response({'message': 'start_location ├® obrigat├│rio.'}, status=400)
        trip.start_location = start_location

    if 'end_location' in data:
        end_location = str(data['end_location']).strip()
        if end_location == '':
            return Response({'message': 'end_location ├® obrigat├│rio.'}, status=400)
        trip.end_location = end_location

    if 'n_people' in data:
        trip.n_people = data['n_people']

    if 'n_kms' in data:
        trip.n_kms = data['n_kms']

    if 'price' in data:
        trip.price = data['price']

    if 'status_trip' in data:
        trip.status_trip = data['status_trip']

    try:
        trip.save()
    except IntegrityError as e:
        return Response({'message': f'Erro ao atualizar trip: {str(e)}'}, status=409)

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
        return Response({'message': 'Trip n├úo encontrada.'}, status=404)

    if trip.status_trip != "pending":
        return Response({"message": "Trip n├úo est├í dispon├¡vel para aceitar."}, status=400)

    driver_id = request.data.get('driver_id')
    if not driver_id:
        return Response({'message': 'driver_id ├® obrigat├│rio.'}, status=400)
    
    if not Driver.objects.filter(pk=driver_id).exists():
        return Response({'message': 'Motorista inv├ílido.'}, status=400)
    
    agora = timezone.now()

    turno_ativo = Shift.objects.filter(
        driver_id=driver.id,
        status_shift__in=["active"],
        start_date__lte=agora,
        end_date__gt=agora,
    ).first()

    if not turno_ativo:
        return Response(
            {"message": "O motorista só pode aceitar pedidos durante um turno ativo."},
            status=400,
        )
    
    trip.driver_id = driver_id
    trip.status_trip = "accepted"
    
    # Tentar atribuir o shift ativo do motorista (se existir)
    try:
        from apps.shift.models import Shift
        from django.utils import timezone
        
        # Buscar shift ativo do motorista
        # Procurar primeiro por um shift que cobre o horário atual
        now = timezone.now()
        active_shift = Shift.objects.filter(
            driver_id=driver_id,
            status_shift='active',
            start_date__lte=now,
            end_date__gte=now
        ).first()
        
        # Se não encontrar um que cobre agora, pegar o mais recente ativo
        if not active_shift:
            active_shift = Shift.objects.filter(
                driver_id=driver_id,
                status_shift='active'
            ).order_by('-start_date').first()
        
        print(f"[TRIP] Accept - Procurando shift para driver {driver_id}, agora: {now}")
        print(f"[TRIP] Accept - Shift encontrado: {active_shift}")
        
        if active_shift:
            trip.shift_id = active_shift.id
            trip.taxi_id = active_shift.taxi_id
            print(f"[TRIP] Accept - Atribuído shift {active_shift.id}, taxi {active_shift.taxi_id}")
    except Exception as e:
        print(f"Erro ao atribuir shift: {e}")
    
    trip.save()

    return Response({
        "success": True,
        "message": "Trip aceita com sucesso",
        "trip": trip_para_json(trip)
    }, status=200)


@api_view(['POST'])
def finish_trip(request, pk):
    from django.utils import timezone
    
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response({'message': 'Trip n├úo encontrada.'}, status=404)

    trip.status_trip = "finished"
    trip.end_date = timezone.now()
    trip.save()

    return Response({
        "success": True,
        "message": "Trip finalizada com sucesso",
        "trip": trip_para_json(trip)
    }, status=200)


@api_view(['POST'])
def reject_trip(request, pk):
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response({'message': 'Trip n├úo encontrada.'}, status=404)

    if trip.status_trip != "pending":
        return Response({"message": "Trip n├úo est├í dispon├¡vel para rejeitar."}, status=400)

    trip.status_trip = "cancelled"
    trip.save()

    return Response({
        "success": True,
        "message": "Trip rejeitada com sucesso",
        "trip": trip_para_json(trip)
    }, status=200)


# ---------------------------------------------------------------------------
# Pagamentos com Stripe
# ---------------------------------------------------------------------------


@api_view(['POST'])
def criar_pagamento(request):
    """
    Cria uma inten├º├úo de pagamento Stripe para uma viagem.
    
    Body esperado:
    {
        "amount": 2500,      # em centavos (25.00 EUR)
        "trip_id": "uuid-da-viagem",
        "description": "Viagem de Uber"  # opcional
    }
    """
    if not stripe.api_key:
        return Response(
            {'message': 'Stripe n├úo est├í configurado no servidor'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    data = request.data or {}
    amount = data.get('amount')
    trip_id = data.get('trip_id')
    description = data.get('description', 'Pagamento de Viagem')
    
    # Validar campos obrigat├│rios
    if not amount or not trip_id:
        return Response(
            {'message': 'amount e trip_id s├úo obrigat├│rios'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validar que a viagem existe
    try:
        trip = Trip.objects.get(pk=trip_id)
    except Trip.DoesNotExist:
        return Response(
            {'message': 'Viagem n├úo encontrada'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Validar amount
    try:
        amount_int = int(amount)
        if amount_int <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return Response(
            {'message': 'amount deve ser um n├║mero positivo em centavos'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Criar payment intent no Stripe
        intent = stripe.PaymentIntent.create(
            amount=amount_int,
            currency='eur',
            description=description,
            metadata={
                'trip_id': str(trip_id),
                'client_id': str(trip.client_id)
            }
        )
        
        return Response({
            'success': True,
            'client_secret': intent.client_secret,
            'payment_intent_id': intent.id,
            'amount': amount_int,
            'currency': 'eur'
        }, status=status.HTTP_200_OK)
        
    except stripe.error.StripeError as e:
        return Response(
            {'message': f'Erro Stripe: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'message': f'Erro ao processar pagamento: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def confirmar_pagamento(request):
    """
    Confirma o pagamento e atualiza o status da viagem.
    
    Body esperado:
    {
        "payment_intent_id": "pi_xxxxx",
        "trip_id": "uuid-da-viagem"
    }
    """
    if not stripe.api_key:
        return Response(
            {'message': 'Stripe n├úo est├í configurado no servidor'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    data = request.data or {}
    payment_intent_id = data.get('payment_intent_id')
    trip_id = data.get('trip_id')
    
    if not payment_intent_id or not trip_id:
        return Response(
            {'message': 'payment_intent_id e trip_id s├úo obrigat├│rios'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Verificar o status do payment intent no Stripe
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if intent.status == 'succeeded':
            # Atualizar o status da viagem
            try:
                from django.utils import timezone
                trip = Trip.objects.get(pk=trip_id)
                trip.status_trip = 'finished'
                trip.end_date = timezone.now()
                trip.save()
                
                return Response({
                    'success': True,
                    'message': 'Pagamento confirmado com sucesso',
                    'trip': trip_para_json(trip)
                }, status=status.HTTP_200_OK)
                
            except Trip.DoesNotExist:
                return Response(
                    {'message': 'Viagem n├úo encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            return Response(
                {'message': f'Pagamento n├úo foi confirmado. Status: {intent.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except stripe.error.StripeError as e:
        return Response(
            {'message': f'Erro ao verificar pagamento: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
def listar_viagens_motorista(request, driver_id):
    """Lista todas as viagens finalizadas de um motorista (para emitir faturas)"""
    try:
        viagens = Trip.objects.filter(
            driver_id=driver_id,
            status_trip='finished'
        ).order_by('-start_date')
        
        resultado = []
        for trip in viagens:
            resultado.append(trip_para_json(trip))
        
        return Response(
            {
                'success': True,
                'driver_id': str(driver_id),
                'trips': resultado,
                'total': len(resultado),
            },
            status=200,
        )
    except Exception as e:
        return Response(
            {'message': f'Erro ao listar viagens: {str(e)}'},
            status=400,
        )
