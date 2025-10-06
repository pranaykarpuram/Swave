from django.urls import path
from .views import test_itunes

urlpatterns = [
    path("test-itunes/", test_itunes),
]
