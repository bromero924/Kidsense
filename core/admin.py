from django.contrib import admin
from .models import ChildProfile, GameSession, Metrics


@admin.register(ChildProfile)
class ChildProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'age', 'parent', 'difficulty_level')
    search_fields = ('name', 'parent__username')


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'child', 'game_type',
                    'started_at', 'duration_seconds')
    list_filter = ('game_type', 'started_at')


@admin.register(Metrics)
class MetricsAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'accuracy',
                    'reaction_time', 'errors', 'score')
