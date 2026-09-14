from django.urls import path

from .views import analyze_cough

urlpatterns = [path("analyze/", analyze_cough, name="analyze-cough")]
