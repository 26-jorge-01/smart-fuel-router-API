from django.urls import path
from routing.api.views import RoutePlanView

urlpatterns = [
    path('route-plan/', RoutePlanView.as_view(), name='route-plan'),
]
