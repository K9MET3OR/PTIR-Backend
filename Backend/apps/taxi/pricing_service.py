"""
Serviço de cálculo de preço de viagens.
Baseado em duração, nível de conforto e agravamento noturno.
"""

from decimal import Decimal
from datetime import timedelta

from django.utils import timezone


class PricingService:
    """
    Calcula o preço de uma viagem conforme User Story 3:
    - preço por minuto por nível de conforto;
    - acréscimo noturno das 21h às 6h.
    """

    DEFAULT_PRICE_PER_MINUTE = {
        "Básico": Decimal("0.25"),
        "Luxuoso": Decimal("0.40"),
    }

    DEFAULT_NIGHT_SURCHARGE = Decimal("0.20")

    NIGHT_START = 21
    NIGHT_END = 6

    MINIMUM_PRICE = Decimal("0.51")

    @classmethod
    def _get_config_values(cls):
        """
        Vai buscar os preços configurados pelo gestor.
        Se algo falhar, usa valores por defeito.
        """
        try:
            from .models import PricingConfig

            config = PricingConfig.get_config()

            return {
                "price_per_minute": {
                    "Básico": Decimal(str(config.preco_basico_minuto)),
                    "Luxuoso": Decimal(str(config.preco_luxuoso_minuto)),
                },
                "night_surcharge": Decimal(str(config.agravamento_noturno_percentual)) / Decimal("100"),
            }
        except Exception:
            return {
                "price_per_minute": cls.DEFAULT_PRICE_PER_MINUTE,
                "night_surcharge": cls.DEFAULT_NIGHT_SURCHARGE,
            }

    @classmethod
    def calculate_price(cls, start_datetime, end_datetime, comfort_level: str) -> dict:
        """
        Calcula o preço de uma viagem apenas pelo tempo, com acréscimo noturno.
        """

        config = cls._get_config_values()
        price_per_minute_map = config["price_per_minute"]
        night_surcharge = config["night_surcharge"]

        if comfort_level not in price_per_minute_map:
            raise ValueError(f"Nível de conforto inválido: {comfort_level}")

        if end_datetime <= start_datetime:
            raise ValueError("Data/hora final deve ser depois da inicial")

        total_minutes = int((end_datetime - start_datetime).total_seconds() // 60)

        if total_minutes <= 0:
            raise ValueError("Duração inválida")

        day_minutes, night_minutes = cls._split_day_night_minutes(
            start_datetime,
            end_datetime
        )

        price_per_minute = price_per_minute_map[comfort_level]

        price_day = Decimal(day_minutes) * price_per_minute
        price_night = (
            Decimal(night_minutes)
            * price_per_minute
            * (Decimal("1.0") + night_surcharge)
        )

        raw_total_price = price_day + price_night
        total_price = raw_total_price.quantize(Decimal("0.01"))

        if total_price < cls.MINIMUM_PRICE:
            total_price = cls.MINIMUM_PRICE

        return {
            "price": float(total_price),
            "breakdown": {
                "day_minutes": day_minutes,
                "night_minutes": night_minutes,
                "price_per_minute": float(price_per_minute),
                "night_surcharge": float(night_surcharge),
                "night_surcharge_percent": float(night_surcharge * Decimal("100")),
                "price_day": float(price_day.quantize(Decimal("0.01"))),
                "price_night": float(price_night.quantize(Decimal("0.01"))),
                "raw_total_price": float(raw_total_price.quantize(Decimal("0.01"))),
                "minimum_price_applied": total_price == cls.MINIMUM_PRICE,
                "minimum_price": float(cls.MINIMUM_PRICE),
            },
            "comfort_level": comfort_level,
        }

    @classmethod
    def _split_day_night_minutes(cls, start_dt, end_dt):
        """
        Conta minutos diurnos e noturnos entre dois datetimes.
        Noite: 21h às 6h.
        """
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

    @classmethod
    def calculate_price_by_distance(
        cls,
        distance_km: float,
        duration_minutes: int,
        comfort_level: str,
        start_datetime=None,
    ) -> dict:
        """
        Calcula o preço de uma viagem por duração estimada.
        A distância é validada e devolvida no breakdown.
        """

        if distance_km <= 0:
            raise ValueError("Distância inválida")

        if duration_minutes <= 0:
            raise ValueError("Duração inválida")

        start_dt = start_datetime or timezone.localtime()
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        result = cls.calculate_price(start_dt, end_dt, comfort_level)

        result["breakdown"]["distance_km"] = distance_km
        result["breakdown"]["duration_minutes"] = duration_minutes

        return result