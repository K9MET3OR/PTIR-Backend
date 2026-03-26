from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.user.utils import validar_nif

from .services import create_admin, login_admin
from .validators import validate_admin_payload


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
