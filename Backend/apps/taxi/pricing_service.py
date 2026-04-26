"""
Serviço de cálculo de preço de viagens.
Baseado em distância (km), duração (minutos) e nível de conforto.
"""

from decimal import Decimal

class PricingService:
    """
    Calcula o preço de uma viagem conforme User Story 3:
    - Preço por minuto (por nível de conforto)
    - Acréscimo noturno (21h-6h)
    """

    # Preço por minuto por nível de conforto
    PRICE_PER_MINUTE = {
        "Básico": Decimal("0.25"),
        "Luxuoso": Decimal("0.40"),
    }
    # Acréscimo noturno em percentagem (ex: 0.20 = 20%)
    NIGHT_SURCHARGE = Decimal("0.20")
    NIGHT_START = 21  # 21h
    NIGHT_END = 6     # 6h

    @classmethod
    def calculate_price(cls, start_datetime, end_datetime, comfort_level: str) -> dict:
        """
        Calcula o preço de uma viagem apenas pelo tempo, com acréscimo noturno.
        Args:
            start_datetime: datetime.datetime de início
            end_datetime: datetime.datetime de fim
            comfort_level: 'Básico' ou 'Luxuoso'
        Returns:
            dict com preço final e breakdown
        """
        from datetime import timedelta
        if comfort_level not in cls.PRICE_PER_MINUTE:
            raise ValueError(f"Nível de conforto inválido: {comfort_level}")
        if end_datetime <= start_datetime:
            raise ValueError("Data/hora final deve ser depois da inicial")

        total_minutes = int((end_datetime - start_datetime).total_seconds() // 60)
        if total_minutes <= 0:
            raise ValueError("Duração inválida")

        # Conta minutos diurnos e noturnos
        day_minutes, night_minutes = cls._split_day_night_minutes(start_datetime, end_datetime)
        price_per_minute = cls.PRICE_PER_MINUTE[comfort_level]
        night_surcharge = cls.NIGHT_SURCHARGE

        price_day = Decimal(day_minutes) * price_per_minute
        price_night = Decimal(night_minutes) * price_per_minute * (Decimal("1.0") + night_surcharge)
        total_price = price_day + price_night
        total_price = total_price.quantize(Decimal("0.01"))

        return {
            "price": float(total_price),
            "breakdown": {
                "day_minutes": day_minutes,
                "night_minutes": night_minutes,
                "price_per_minute": float(price_per_minute),
                "night_surcharge": float(night_surcharge),
                "price_day": float(price_day),
                "price_night": float(price_night),
            },
            "comfort_level": comfort_level,
        }

    @classmethod
    def _split_day_night_minutes(cls, start_dt, end_dt):
        """Conta minutos diurnos e noturnos entre dois datetimes."""
        from datetime import timedelta
        current = start_dt
        day = 0
        night = 0
        while current < end_dt:
            hour = current.hour
            if hour >= cls.NIGHT_START or hour < cls.NIGHT_END:
                night += 1
            else:
                day += 1
            current += timedelta(minutes=1)
        return day, night
