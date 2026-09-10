from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from . import views

# Main router
router = DefaultRouter()
router.register(r'countries', views.CountryViewSet, basename='country')
router.register(r'districts', views.DistrictViewSet, basename='district')
router.register(r'circunscricoes', views.CircunscricaoViewSet, basename='circunscricao')
router.register(r'polling-stations', views.PollingStationViewSet, basename='pollingstation')
router.register(r'parties', views.PartyViewSet, basename='party')
router.register(r'votetables', views.VoteTableViewSet, basename='votetable')
router.register(r'voteentries', views.VoteEntryViewSet, basename='voteentry')

# Nested routers
countries_router = routers.NestedDefaultRouter(router, r'countries', lookup='country')
countries_router.register(r'districts', views.CountryDistrictsViewSet, basename='country-districts')
countries_router.register(r'results', views.ResultPerCountryViewSet, basename='country-results')

districts_router = routers.NestedDefaultRouter(router, r'districts', lookup='district')
districts_router.register(r'circunscricoes', views.DistrictCircunscricoesViewSet, basename='district-circunscricoes')
districts_router.register(r'votetables', views.VoteTableViewSet, basename='district-votetables')
districts_router.register(r'results', views.ResultPerDistrictViewSet, basename='district-results')

circunscricoes_router = routers.NestedDefaultRouter(router, r'circunscricoes', lookup='circunscricao')
circunscricoes_router.register(r'polling-stations', views.CircunscricaoPollingStationsViewSet, basename='circunscricao-pollingstations')
circunscricoes_router.register(r'votetables', views.VoteTableViewSet, basename='circunscricao-votetables')
circunscricoes_router.register(r'results', views.ResultPerCircunscricaoViewSet, basename='circunscricao-results')

votetables_router = routers.NestedDefaultRouter(router, r'votetables', lookup='vote_table')
votetables_router.register(r'voteentries', views.VoteEntryViewSet, basename='votetable-voteentries')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(countries_router.urls)),
    path('', include(districts_router.urls)),
    path('', include(circunscricoes_router.urls)),
    path('', include(votetables_router.urls)),
]