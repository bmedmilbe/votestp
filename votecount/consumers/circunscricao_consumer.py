
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from votecount.models import Circunscricao
from votecount.serializers import (
    NestedCircunscricaoSerializer,
)


class ResultCircunscricaoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs'].get('circunscricao_id')
        self.room_group_name = f'result_circunscricao_{self.room_name}'
        
        await self.channel_layer.group_add(
            self.room_group_name,  
            self.channel_name
        )

        await self.accept()
       
        results_circunscricao = await self.results_circunscricao_per_party(self.room_name)

        await self.send(text_data=json.dumps({
            'type': 'result_circunscricao',
            'data': results_circunscricao
        }))

    async def result_circunscricao(self, event):
        await self.send(text_data=json.dumps({
            'type': 'result_circunscricao',
            'data': event['data'],
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    @database_sync_to_async
    def results_circunscricao_per_party(self, room_name):        
        circunscricao = Circunscricao.objects.get(id=room_name)
    
        serializer =  NestedCircunscricaoSerializer(circunscricao)

        data = serializer.data
        
        return data

    
    