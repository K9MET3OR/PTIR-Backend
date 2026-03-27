from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.user.utils import validar_nif

from .services import create_client, login_client
from .validators import validate_client_payload


@api_view(['POST'])
def registo_client(request):
	data = request.data
	err = validate_client_payload(data)
	if err:
		return Response({'message': err}, status=400)

	user, service_err, status_code = create_client(data)
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
def login_client_nif(request):
	nif = str(request.data.get('nif', '')).strip()
	if not validar_nif(nif):
		return Response({'message': 'NIF invalido.'}, status=400)

	payload, service_err, status_code = login_client(request.data)
	if service_err:
		return Response({'message': service_err}, status=status_code)

	return Response(payload, status=200)
