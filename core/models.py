from django.db import models
from django.contrib.auth.models import User


class ChildProfile(models.Model):
    parent = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    difficulty_level = models.CharField(max_length=20, default='Moderate')

    def __str__(self):
        return self.name


class GameSession(models.Model):
    GAME_TYPES = [
        ('follow_star', 'Follow Star'),

    ]
    child = models.ForeignKey(ChildProfile, on_delete=models.CASCADE)
    game_type = models.CharField(max_length=50, choices=GAME_TYPES)
    started_at = models.DateTimeField(auto_now_add=True)
    duration_seconds = models.FloatField(default=0)

    def __str__(self):
        return f"{self.child.name} - {self.game_type}"


class Metrics(models.Model):
    session = models.OneToOneField(GameSession, on_delete=models.CASCADE)
    accuracy = models.FloatField(default=0)
    reaction_time = models.FloatField(default=0)
    errors = models.PositiveIntegerField(default=0)
    score = models.FloatField(default=0)
    final_speed = models.IntegerField(default=0)
    system_action = models.CharField(max_length=50, blank=True, null=True)
    alert_triggered = models.BooleanField(default=False)

    def __str__(self):
        return f'Metrics fro session {self.session.id}'


class Alert(models.Model):
    child = models.ForeignKey(
        ChildProfile,
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    session = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    message = models.TextField()
    system_action = models.CharField(max_length=100, blank=True, null=True)
    score = models.FloatField(blank=True, null=True)
    sent_sms = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.child.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
