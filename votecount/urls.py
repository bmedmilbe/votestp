from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'countries', views.CountryViewSet)
router.register(r'districts', views.DistrictViewSet)
router.register(r'circunscricoes', views.CircunscricaoViewSet)
router.register(r'polling-stations', views.PollingStationViewSet)
router.register(r'parties', views.PartyViewSet)
router.register(r'vote-tables', views.VoteTableViewSet)
router.register(r'vote-entries', views.VoteEntryViewSet)
router.register(r'vote-results', views.VoteResultViewSet)
router.register(r'hondt-calculations', views.HondtCalculationViewSet)
router.register(r'dashboard', views.DashboardViewSet, basename='dashboard')
router.register(r'reports', views.ReportViewSet, basename='reports')
router.register(r'agents', views.AgentViewSet)
router.register(r'imports', views.OriginalDataImportViewSet)

urlpatterns = [
    path('', include(router.urls)),
]