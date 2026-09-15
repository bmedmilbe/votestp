import os

from django.core.asgi import get_asgi_application

# 1. Set environment variables first
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voteapp.settings.dev")

# 2. Initialize the Django ASGI application immediately to load the App Registry
django_asgi_app = get_asgi_application()

# 3. Import Channels components, custom middleware, and consumers ONLY after initialization
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path

from core.middleware import TokenAuthMiddlewareStack
from votecount.consumers.circunscricao_consumer import ResultCircunscricaoConsumer
from votecount.consumers.country_consumer import ResultCountryConsumer
from votecount.consumers.district_consumer import ResultDistrictConsumer

# 4. Define the final routing map using the pre-initialized application
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": TokenAuthMiddlewareStack(
            URLRouter(
                [
                    path(
                        "ws/results/country/<int:country_id>/",
                        ResultCountryConsumer.as_asgi(),
                    ),
                    path(
                        "ws/results/district/<int:district_id>/",
                        ResultDistrictConsumer.as_asgi(),
                    ),
                    path(
                        "ws/results/circunscricao/<int:circunscricao_id>/",
                        ResultCircunscricaoConsumer.as_asgi(),
                    ),
                ]
            )
        ),
    }
)
