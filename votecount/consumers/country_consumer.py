import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from votecount.models import Country
from votecount.serializers import NestedCountrySerializer


class ResultCountryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"].get("country_id")
        self.room_group_name = f"result_country_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        results_country = await self.results_country_per_party(self.room_name)

        await self.send(
            text_data=json.dumps({"type": "result_country", "data": results_country})
        )

    async def result_country(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "result_country",
                    "data": event["data"],
                }
            )
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    @database_sync_to_async
    def results_country_per_party(self, room_name):
        country = Country.objects.get(id=room_name)

        serializer = NestedCountrySerializer(country)

        data = serializer.data

        return data
