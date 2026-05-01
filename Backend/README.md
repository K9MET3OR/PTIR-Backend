# PTIR02
Projecto Tecnologias informações e redes Grupo 2


## docker-compose up --build

## API (localhost:8000)
#### api/user/
- api/user/ (Listar Users);
- api/user/login (Login);
- api/user/<uuid:id> (Get User);
- api/user/<uuid:id>/update (Update User);
- api/user/<uuid:id>/delete (Delete User)

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

#### api/client/
- api/client/ (Listar Clients)
- api/client/register (Register)
- api/client/login (Login)
- api/client/<uuid:id_client> (Update Client)

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

#### api/driver/
- api/driver/ (Listar Drivers)
- api/driver/register (Register)
- api/driver/login (Login)
- api/driver/localidade/<str:codigo_postal> (Get Localidade)
- api/driver/<uuid:id_motorista> (Update Motorista)
- api/driver/<uuid:id_motorista>/estado (Update Motorista Estado)

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

#### api/admin/
- api/admin/ (Listar Admin)
- api/admin/register (Register)
- api/admin/login (Login)
- api/admin/<uuid:id_admin> (Update Admin)

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

#### api/taxi/
- api/taxi/ (Listar Taxis)
- api/taxi/register (Register)
- api/taxi/calcucate-travel-cost (Calculate Travel Cost)
- api/taxi/calculate-price-comfortably (Calculate Price Comfortably)
- api/taxi/<uuid:id_taxi>/remove (Remove Taxi)
- api/taxi/<uuid:id_taxi>/estado (Update Taxi Estado)
- api/taxi/<uuid:id_taxi>/localizacao (Update)
- api/taxi/<uuid:id_taxi> (Update Taxi)

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

#### api/trip/
- api/trip/ (Listar Trip)
- api/trip/register (Register)
- api/trip/<uuid:id_trip> (Update Trip)
- api/trip/<uuid:pk>/accept (Accept Trip)
- api/trip/<uuid:pk>/reject (Reject Trip)
- api/trip/<uuid:pk>/finish (Finish Trip)
- api/trip/pagamento/create (Create Payment)
- api/trip/pagamento/confirm (Confirm Payment)

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

#### api/shift/
- api/shift/ (Listar Shifts)
- api/shift/register (Register)
- api/shift/taxis-available (Listar Taxis Available)
- api/shift/driver/<uuid:driver_id> (Listar Driver Shift)
- api/shift/<uuid:id_shift>/finish (Finish Shift)
- api/shift/<uuid:id_shift> (Update Shift)

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

#### api/invoice/

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

#### api/refuel/
