from django.urls import path
from .views import home, create_child, child_detail, save_game_result, privacy_view, terms_view

urlpatterns = [
    path('', home, name='home'),
    path('child/create/', create_child, name='create_child'),
    path('child/<int:child_id>/', child_detail, name='child_detail'),
    path('child/<int:child_id>/save-result/',
         save_game_result, name='save_game_result'),
    path('privacy/', privacy_view, name='privacy'),
    path('terms/', terms_view, name='terms'),
]
