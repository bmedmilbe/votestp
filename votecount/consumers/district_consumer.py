import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from votecount.models import District
from votecount.serializers import NestedDistrictSerializer


class ResultDistrictConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"].get("district_id")
        self.room_group_name = f"result_district_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        results_district = await self.results_district_per_party(self.room_name)

        await self.send(
            text_data=json.dumps({"type": "result_district", "data": results_district})
        )

    async def result_district(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "result_district",
                    "data": event["data"],
                }
            )
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    @database_sync_to_async
    def results_district_per_party(self, room_name):
        district = District.objects.get(id=room_name)

        serializer = NestedDistrictSerializer(district)

        data = serializer.data

        return data
