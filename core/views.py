
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import TokenCreateSerializer


class UserTokenObtainPairView(TokenObtainPairView):
    serializer_class = TokenCreateSerializer