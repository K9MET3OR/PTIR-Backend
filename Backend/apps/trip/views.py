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
from apps.user.driver.models import Driver
from apps.shift.models import Shift
from decimal import Decimal, InvalidOperation

stripe.api_key = settings.STRIPE_SECRET_KEY if hasattr(settings, 'STRIPE_SECRET_KEY') else None

def valor_positivo(valor):
    try:
        return Decimal(str(valor)) > 0
    except (InvalidOperation, TypeError, ValueError):
        return False


def validar_restricoes_trip(trip):
    try:
        n_people = int(trip.n_people)
    except (TypeError, ValueError):
        return "O número de pessoas é inválido."

    if n_people < 1 or n_people > 4:
        return "O número de pessoas deve estar entre 1 e 4."

    if trip.n_kms is None or not valor_positivo(trip.n_kms):
        return "Os quilómetros percorridos têm de ser positivos."

    if trip.price is None or not valor_positivo(trip.price):
        return "O preço da viagem tem de ser positivo."

    return None


def motorista_tem_viagem_em_curso(driver_id, trip_id_atual=None):
    viagens = Trip.objects.filter(
        driver_id=driver_id,
        status_trip__in=[
            "driver_accepted",
            "client_confirmed",
            "in_progress",
            "awaiting_payment",
        ],
    )

    if trip_id_atual:
        viagens = viagens.exclude(pk=trip_id_atual)

    return viagens.exists()

def normalizar_conforto(valor):
    texto = str(valor or '').strip().lower()

    if texto in ['luxuoso', 'luxo']:
        return 'luxuoso'

    return 'básico'

def existe_sobreposicao_viagem(trip, inicio, fim):
    if not trip.driver_id:
        return False

    return Trip.objects.filter(
        driver_id=trip.driver_id,
        start_date__isnull=False,
        end_date__isnull=False,
        start_date__lt=fim,
        end_date__gt=inicio,
        status_trip__in=["awaiting_payment", "finished"],
    ).exclude(pk=trip.pk).exists()


def trip_para_json(trip):
    driver_name = None
    if trip.driver_id:
        try:
            driver = Driver.objects.get(pk=trip.driver_id)
            driver_name = driver.name or "Motorista"
        except Exception:
            driver_name = "Motorista"

    taxi_matricula = None
    taxi_id = trip.taxi_id

    if not taxi_id and trip.shift_id:
        try:
            shift = Shift.objects.get(pk=trip.shift_id)
            taxi_id = shift.taxi_id
        except Exception:
            taxi_id = None

    if taxi_id:
        try:
            from apps.taxi.models import Taxi
            taxi = Taxi.objects.get(pk=taxi_id)
            taxi_matricula = taxi.matricula
        except Exception:
            taxi_matricula = "N/A"
    else:
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
        'rejected_driver_ids': trip.rejected_driver_ids or [],
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

    for campo in campos_obrigatorios:
        if campo not in data or str(data[campo]).strip() == '':
            return Response({'message': f'{campo} é obrigatório.'}, status=400)

    try:
        n_people = int(data['n_people'])
    except (TypeError, ValueError):
        return Response({'message': 'n_people inválido.'}, status=400)

    if n_people < 1 or n_people > 4:
        return Response({'message': 'n_people deve estar entre 1 e 4.'}, status=400)

    try:
        user = User.objects.get(pk=data['client_id'], role='cliente')
    except User.DoesNotExist:
        return Response({'message': 'Cliente inválido.'}, status=400)

    client = Client.objects.filter(pk=user.pk).first()
    if not client:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO clients (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                [user.pk],
            )
        client = Client.objects.get(pk=user.pk)

    start_date = data.get('start_date')
    if start_date:
        start_date = parse_datetime(start_date)
        if start_date is None:
            return Response({'message': 'start_date inválida.'}, status=400)
    else:
        start_date = timezone.now()

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
            nivel_conforto=data.get('nivel_conforto', 'Básico'),
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
            return Response({'message': 'start_location é obrigatório.'}, status=400)
        trip.start_location = start_location

    if 'end_location' in data:
        end_location = str(data['end_location']).strip()
        if end_location == '':
            return Response({'message': 'end_location é obrigatório.'}, status=400)
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
        return Response({'message': 'Trip não encontrada.'}, status=404)

    if trip.status_trip != "pending":
        return Response({"message": "Trip não está disponível para aceitar."}, status=400)

    driver_id = request.data.get('driver_id')
    if not driver_id:
        return Response({'message': 'driver_id é obrigatório.'}, status=400)

    try:
        driver = Driver.objects.get(pk=driver_id)
    except Driver.DoesNotExist:
        return Response({'message': 'Motorista inválido.'}, status=400)

    rejected_ids = [str(driver_uuid) for driver_uuid in (trip.rejected_driver_ids or [])]

    if str(driver.id) in rejected_ids:
        return Response(
            {"message": "Este pedido já rejeitou este motorista."},
            status=400,
        )

    agora = timezone.now()

    turno_ativo = Shift.objects.filter(
        driver_id=driver.id,
        start_date__lte=agora,
        end_date__gt=agora,
    ).exclude(status_shift='inactive').first()

    if not turno_ativo:
        return Response(
            {"message": "Só podes aceitar pedidos durante um turno ativo."},
            status=400,
        )
    
    try:
        taxi_turno = turno_ativo.taxi
    except Exception:
        taxi_turno = None

    if not taxi_turno:
        return Response(
            {"message": "O turno ativo não tem táxi associado."},
            status=400,
        )

    if normalizar_conforto(taxi_turno.nivel_conforto) != normalizar_conforto(trip.nivel_conforto):
        return Response(
            {
                "message": (
                    "Este pedido exige um nível de conforto diferente "
                    "do táxi associado ao teu turno."
                )
            },
            status=400,
        )

    if motorista_tem_viagem_em_curso(driver.id):
        return Response(
            {"message": "Não podes aceitar outro pedido enquanto tens uma viagem ou pedido em curso."},
            status=400,
        )

    try:
        n_people = int(trip.n_people)
    except (TypeError, ValueError):
        return Response({"message": "O número de pessoas é inválido."}, status=400)

    if n_people < 1 or n_people > 4:
        return Response(
            {"message": "O número de pessoas deve estar entre 1 e 4."},
            status=400,
        )

    trip.driver_id = driver.id
    trip.shift_id = turno_ativo.id
    trip.taxi_id = turno_ativo.taxi_id
    trip.status_trip = "driver_accepted"

    trip.save()

    return Response({
        "success": True,
        "message": "Trip aceita com sucesso",
        "trip": trip_para_json(trip)
    }, status=200)

@api_view(['POST'])
def client_confirm_trip(request, pk):
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response({'message': 'Trip não encontrada.'}, status=404)

    if trip.status_trip != "driver_accepted":
        return Response(
            {'message': 'Esta viagem não está à espera de confirmação do cliente.'},
            status=400
        )

    trip.status_trip = "client_confirmed"
    trip.save()

    return Response({
        'success': True,
        'message': 'Motorista confirmado com sucesso.',
        'trip': trip_para_json(trip)
    }, status=200)


@api_view(['POST'])
def client_reject_trip(request, pk):
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response({'message': 'Trip não encontrada.'}, status=404)

    if trip.status_trip != "driver_accepted":
        return Response(
            {'message': 'Esta viagem não está à espera de confirmação do cliente.'},
            status=400
        )

    rejected_ids = [str(driver_uuid) for driver_uuid in (trip.rejected_driver_ids or [])]

    if trip.driver_id and str(trip.driver_id) not in rejected_ids:
        rejected_ids.append(str(trip.driver_id))

    trip.rejected_driver_ids = rejected_ids
    trip.driver_id = None
    trip.taxi_id = None
    trip.shift_id = None
    trip.status_trip = "pending"
    trip.save()

    return Response({
        'success': True,
        'message': 'Motorista rejeitado. O pedido voltou a ficar pendente.',
        'trip': trip_para_json(trip)
    }, status=200)

@api_view(['POST'])
def start_trip(request, pk):
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response({'message': 'Trip não encontrada.'}, status=404)

    if trip.status_trip != "client_confirmed":
        return Response(
            {'message': 'Só é possível iniciar uma viagem confirmada pelo cliente.'},
            status=400
        )

    if not trip.driver_id:
        return Response(
            {'message': 'Esta viagem não tem motorista associado.'},
            status=400
        )

    if not trip.shift_id:
        return Response(
            {'message': 'Esta viagem não tem turno associado.'},
            status=400
        )

    agora = timezone.now()

    try:
        shift = Shift.objects.get(pk=trip.shift_id)
    except Shift.DoesNotExist:
        return Response({'message': 'Turno inválido.'}, status=400)

    if shift.status_shift == "inactive":
        return Response(
            {'message': 'Não é possível iniciar uma viagem num turno inativo.'},
            status=400
        )

    if not (shift.start_date <= agora < shift.end_date):
        return Response(
            {'message': 'A viagem só pode ser iniciada dentro do período do turno.'},
            status=400
        )

    if motorista_tem_viagem_em_curso(trip.driver_id, trip.pk):
        return Response(
            {'message': 'O motorista já tem outra viagem ou pedido em curso.'},
            status=400
        )

    try:
        n_people = int(trip.n_people)
    except (TypeError, ValueError):
        return Response({'message': 'O número de pessoas é inválido.'}, status=400)

    if n_people < 1 or n_people > 4:
        return Response(
            {'message': 'O número de pessoas deve estar entre 1 e 4.'},
            status=400
        )

    trip.status_trip = "in_progress"
    trip.start_date = agora
    trip.end_date = None
    trip.save()

    return Response({
        "success": True,
        "message": "Viagem iniciada com sucesso",
        "trip": trip_para_json(trip)
    }, status=200)

@api_view(['POST'])
def finish_trip(request, pk):
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response({'message': 'Trip não encontrada.'}, status=404)

    if trip.status_trip != "in_progress":
        return Response(
            {'message': 'Só é possível terminar uma viagem que esteja em progresso.'},
            status=400
        )

    if not trip.start_date:
        return Response(
            {'message': 'A viagem não tem hora de início registada.'},
            status=400
        )

    if not trip.shift_id:
        return Response(
            {'message': 'Esta viagem não tem turno associado.'},
            status=400
        )

    fim = timezone.now()

    if trip.start_date >= fim:
        return Response(
            {'message': 'A hora de início da viagem tem de ser anterior à hora de fim.'},
            status=400
        )

    try:
        shift = Shift.objects.get(pk=trip.shift_id)
    except Shift.DoesNotExist:
        return Response({'message': 'Turno inválido.'}, status=400)

    if trip.start_date < shift.start_date or fim > shift.end_date:
        return Response(
            {'message': 'A viagem tem de estar contida no período do turno.'},
            status=400
        )

    erro_restricoes = validar_restricoes_trip(trip)
    if erro_restricoes:
        return Response({'message': erro_restricoes}, status=400)

    if existe_sobreposicao_viagem(trip, trip.start_date, fim):
        return Response(
            {'message': 'Esta viagem não pode sobrepor-se a outra viagem do motorista.'},
            status=400
        )

    trip.status_trip = "awaiting_payment"
    trip.end_date = fim
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
        return Response({'message': 'Trip não encontrada.'}, status=404)

    if trip.status_trip != "pending":
        return Response({"message": "Trip não está disponível para rejeitar."}, status=400)

    trip.status_trip = "cancelled"
    trip.save()

    return Response({
        "success": True,
        "message": "Trip rejeitada com sucesso",
        "trip": trip_para_json(trip)
    }, status=200)


@api_view(['POST'])
def criar_pagamento(request):
    """
    Cria uma intenção de pagamento Stripe para uma viagem.

    Body esperado:
    {
        "amount": 2500,
        "trip_id": "uuid-da-viagem",
        "description": "Viagem de Uber"
    }
    """
    if not stripe.api_key:
        return Response(
            {'message': 'Stripe não está configurado no servidor'},
            status=status.HTTP_400_BAD_REQUEST
        )

    data = request.data or {}
    amount = data.get('amount')
    trip_id = data.get('trip_id')
    description = data.get('description', 'Pagamento de Viagem')

    if not amount or not trip_id:
        return Response(
            {'message': 'amount e trip_id são obrigatórios'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        trip = Trip.objects.get(pk=trip_id)
    except Trip.DoesNotExist:
        return Response(
            {'message': 'Viagem não encontrada'},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        amount_int = int(amount)
        if amount_int <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return Response(
            {'message': 'amount deve ser um número positivo em centavos'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
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
            {'message': 'Stripe não está configurado no servidor'},
            status=status.HTTP_400_BAD_REQUEST
        )

    data = request.data or {}
    payment_intent_id = data.get('payment_intent_id')
    trip_id = data.get('trip_id')

    if not payment_intent_id or not trip_id:
        return Response(
            {'message': 'payment_intent_id e trip_id são obrigatórios'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        if intent.status == 'succeeded':
            try:
                trip = Trip.objects.get(pk=trip_id)
                if trip.status_trip != 'awaiting_payment':
                    return Response(
                        {'message': 'Esta viagem não está à espera de pagamento.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                trip.status_trip = 'finished'

                if not trip.end_date:
                    trip.end_date = timezone.now()

                trip.save()

                return Response({
                    'success': True,
                    'message': 'Pagamento confirmado com sucesso',
                    'trip': trip_para_json(trip)
                }, status=status.HTTP_200_OK)

            except Trip.DoesNotExist:
                return Response(
                    {'message': 'Viagem não encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            return Response(
                {'message': f'Pagamento não foi confirmado. Status: {intent.status}'},
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
    
@api_view(['POST'])
def cancel_driver_wait(request, pk):
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response({'message': 'Trip não encontrada.'}, status=404)

    if trip.status_trip != "driver_accepted":
        return Response(
            {'message': 'Esta viagem não está à espera de confirmação do cliente.'},
            status=400
        )

    rejected_ids = [str(driver_uuid) for driver_uuid in (trip.rejected_driver_ids or [])]

    if trip.driver_id and str(trip.driver_id) not in rejected_ids:
        rejected_ids.append(str(trip.driver_id))

    trip.rejected_driver_ids = rejected_ids
    trip.driver_id = None
    trip.taxi_id = None
    trip.shift_id = None
    trip.status_trip = "pending"
    trip.save()

    return Response({
        'success': True,
        'message': 'Tempo de espera expirado. O pedido voltou a ficar pendente.',
        'trip': trip_para_json(trip)
    }, status=200)