
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path

from core.middleware import TokenAuthMiddlewareStack
from votecount.consumers.circunscricao_consumer import ResultCircunscricaoConsumer
from votecount.consumers.country_consumer import ResultCountryConsumer
from votecount.consumers.district_consumer import ResultDistrictConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voteapp.settings.dev')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': TokenAuthMiddlewareStack(
        URLRouter([
            path('ws/results/country/<int:country_id>', ResultCountryConsumer.as_asgi()),
            path('ws/results/district/<int:district_id>', ResultDistrictConsumer.as_asgi()),
            path('ws/results/circunscricao/<int:circunscricao_id>', ResultCircunscricaoConsumer.as_asgi()),

        ])
    ),
})