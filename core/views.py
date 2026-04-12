from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ChildProfileForm
from .models import ChildProfile, GameSession, Metrics, Alert
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
import json
from twilio.rest import Client
from django.conf import settings


def home(request):
    children_data = []

    if request.user.is_authenticated:
        children = ChildProfile.objects.filter(parent=request.user)

        for child in children:
            sessions = GameSession.objects.filter(
                child=child).order_by('-started_at')

            last_session = sessions.first()
            second_last_session = sessions[1] if sessions.count() > 1 else None

            insight = None
            score = None
            trend = None

            if last_session and hasattr(last_session, 'metrics'):
                score = last_session.metrics.score

                if score >= 80:
                    insight = "Strong"
                elif score >= 50:
                    insight = "Moderate"
                else:
                    insight = "Low"

            if (
                last_session and second_last_session and
                hasattr(last_session, 'metrics') and
                hasattr(second_last_session, 'metrics')
            ):
                latest_score = last_session.metrics.score
                previous_score = second_last_session.metrics.score

                if latest_score > previous_score:
                    trend = "Improving"
                elif latest_score < previous_score:
                    trend = "Declining"
                else:
                    trend = "Stable"

            short_recommendation = "Keep playing regularly."

            if child.difficulty_level == "Low":
                if trend == "Improving":
                    short_recommendation = "Improving slowly."
                elif trend == "Declining":
                    short_recommendation = "Needs easier sessions."
                else:
                    short_recommendation = "Needs support."

            elif child.difficulty_level == "Moderate":
                if trend == "Improving":
                    short_recommendation = "Building consistency."
                elif trend == "Declining":
                    short_recommendation = "Watch recent changes."
                else:
                    short_recommendation = "Keep practicing."

            else:
                if trend == "Improving":
                    short_recommendation = "Doing very well."
                elif trend == "Declining":
                    short_recommendation = "Slight dip recently."
                else:
                    short_recommendation = "Strong engagement."

            children_data.append({
                'child': child,
                'score': score,
                'level': child.difficulty_level,
                'insight': insight,
                'trend': trend,
                'short_recommendation': short_recommendation,

            })

    return render(request, 'core/home.html', {
        'children_data': children_data
    })


@login_required
def create_child(request):
    if request.method == 'POST':
        form = ChildProfileForm(request.POST)
        if form.is_valid():
            child = form.save(commit=False)
            child.parent = request.user
            child.save()
            return redirect('home')
    else:
        form = ChildProfileForm()

    return render(request, 'core/create_child.html', {'form': form})


@login_required
def child_detail(request, child_id):
    child = get_object_or_404(ChildProfile, id=child_id, parent=request.user)
    sessions = GameSession.objects.filter(child=child).order_by('-started_at')

    # -----------------------------
    # SCORES + DATES
    # -----------------------------
    scores = []
    dates = []

    for session in sessions:
        if hasattr(session, 'metrics'):
            scores.append(session.metrics.score)
            dates.append(session.started_at.strftime("%m/%d"))

    recent_scores = scores[:3]
    avg_score = sum(recent_scores) / len(recent_scores) if recent_scores else 0

    # -----------------------------
    # THRESHOLDS BY AGE
    # -----------------------------
    if child.age <= 4:
        low_threshold = 30
        high_threshold = 70
    elif child.age <= 6:
        low_threshold = 40
        high_threshold = 75
    else:
        low_threshold = 50
        high_threshold = 80

    # -----------------------------
    # BASE LEVEL CALCULATION
    # -----------------------------
    latest_score = recent_scores[0] if recent_scores else 0
    final_score = (latest_score * 0.7) + (avg_score * 0.3)

    if final_score < (low_threshold):
        level = "Low"
    elif final_score < (high_threshold):
        level = "Moderate"
    else:
        level = "High"

    # -----------------------------
    # TREND
    # -----------------------------
    trend = "Not enough data"

    if len(recent_scores) >= 2:
        latest_score = recent_scores[0]
        previous_score = recent_scores[1]

        if latest_score > previous_score:
            trend = "Improving"
        elif latest_score < previous_score:
            trend = "Declining"
        else:
            trend = "Stable"

    # -----------------------------
    # RISK LEVEL
    # -----------------------------
    risk_level = "Low Risk"

    if avg_score < 40 and trend == "Declining":
        risk_level = "Needs Attention"
    elif avg_score < 60 or trend == "Declining":
        risk_level = "Monitor"

    # -----------------------------
    # ALERT
    # -----------------------------
    alert = None

    if len(scores) >= 3 and scores[0] < scores[1] < scores[2]:
        alert = "Performance is declining consistently"

    if avg_score < 40 and len(scores) >= 3:
        alert = "Low engagement detected. Consider closer monitoring"

    if trend == "Improving" and avg_score > 70:
        alert = "Strong improvement observed"

    # -----------------------------
    # PERSONALIZED RECOMMENDATION
    # -----------------------------
    personalized_recommendation = "Continue regular play sessions and monitor progress over time."

    # -----------------------------
    # SHORT RECOMMENDATION
    # -----------------------------
    if level == "Low":
        if trend == "Improving":
            recommendation = (
                "Engagement is still low, but improvement is visible. Keep sessions short and consistent."
            )
        elif trend == "Declining":
            recommendation = (
                "Recent performance is dropping. Try shorter sessions and reduce difficulty."
            )
        else:
            recommendation = (
                "Try shorter daily sessions and encourage repeated play."
            )

    elif level == "Moderate":
        if trend == "Improving":
            recommendation = (
                "Progress is improving. Keep practicing regularly to build consistency."
            )
        elif trend == "Declining":
            recommendation = (
                "Performance is becoming less consistent. Maintain routine and observe closely."
            )
        else:
            recommendation = (
                "Keep practicing regularly to improve consistency."
            )

    else:
        if trend == "Improving":
            recommendation = (
                "Strong engagement and continued improvement. Maintain regular sessions."
            )
        elif trend == "Declining":
            recommendation = (
                "Engagement is still strong, but recent performance dipped slightly. Keep practice steady."
            )
        else:
            recommendation = (
                "Great engagement. Continue with regular play sessions."
            )

    # -----------------------------
    # ADAPTIVE ENGINE
    # -----------------------------
    if len(recent_scores) >= 3:
        current_level = child.difficulty_level

        # prevent extreme jumps
        if current_level == "Low" and level == "High":
            level = "Moderate"
        elif current_level == "High" and level == "Low":
            level = "Moderate"

        # drop faster if performance is falling
        if trend == "Declining" and risk_level in ["Monitor", "Needs Attention"]:
            level = "Low"

        # only raise with strong confirmation
        elif trend == "Improving" and risk_level == "Low Risk":
            if recent_scores[0] > high_threshold and recent_scores[1] > high_threshold:
                level = "High"

        if child.difficulty_level != level:
            child.difficulty_level = level
            child.save()

    # -----------------------------
    # INSIGHT FROM LATEST SESSION
    # -----------------------------
    latest_session = sessions.first()
    insight = None
    challenge_tolerance = "Unknown"
    system_action = None
    alert_message = None

    if latest_session and hasattr(latest_session, 'metrics'):
        latest_metric_score = latest_session.metrics.score
        final_speed = latest_session.metrics.final_speed
        system_action = latest_session.metrics.system_action

        if latest_session.metrics.alert_triggered:
            alert_message = "⚠️ Attention: Child may need support"

        if final_speed <= 1200:
            challenge_tolerance = "High"
        elif final_speed <= 2000:
            challenge_tolerance = "Moderate"
        else:
            challenge_tolerance = "Low"

        if latest_metric_score >= 80:
            insight = "Strong attention and interaction in the latest session."
        elif latest_metric_score >= 50:
            insight = "Moderate performance. More play sessions may help improve consistency."
        else:
            insight = "Low interaction in the latest session. Continue observing patterns over time."

    decision_history = []

    for session in sessions[:5]:
        if hasattr(session, 'metrics'):
            decision_history.append({
                'date': session.started_at.strftime('%b %d, %Y %I:%M %p'),
                'score': session.metrics.score,
                'system_action': session.metrics.system_action,
            })

    alert_message = None

    recent_actions = [item['system_action'] for item in decision_history]

    # Regla 1: muchas dificultades
    if recent_actions.count("Reduce Difficulty") >= 3:
        alert_message = "⚠️ Child may be struggling. Consider intervention."

    # Regla 2: muchas mejoras
    elif recent_actions.count("Increase Difficulty") >= 3:
        alert_message = "✅ Child is improving consistently."

    # Regla 3: monitoreo constante
    elif recent_actions.count("Monitor Closely") >= 3:
        alert_message = "⚠️ Performance unstable. Keep monitoring closely."

    recent_alert = []
    for session in sessions[:5]:
        if hasattr(session, 'metrics') and session.metrics.alert_triggered:
            recent_alert.append({
                'date': session.started_at.strftime('%b %d, %y %I:%M %p'),
                'score': session.metrics.score,
                'system_action': session.metrics.system_action,
            })

    return render(request, 'core/child_detail.html', {
        'child': child,
        'sessions': sessions,
        'insight': insight,
        'scores_json': json.dumps(scores),
        'dates_json': json.dumps(dates),
        'level': child.difficulty_level,
        'trend': trend,
        'recommendation': recommendation,
        'difficulty': child.difficulty_level,
        'average_score': avg_score,
        'avg_score': avg_score,
        'alert': alert,
        'personalized_recommendation': personalized_recommendation,
        'risk_level': risk_level,
        'challenge_tolerance': challenge_tolerance,
        'system_action': system_action,
        'decision_history': decision_history,
        'alert_message': alert_message,
        'recent_alert': recent_alert,
    })


@login_required
def save_game_result(request, child_id):
    if request.method == 'POST':
        child = get_object_or_404(
            ChildProfile, id=child_id, parent=request.user
        )

        data = json.loads(request.body)

        hits = data.get('hits', 0)
        moves = data.get('moves', 0)
        duration = data.get('duration', 0)
        final_speed = data.get('final_speed', 0)
        print('FINAL SPEED:', final_speed)

        accuracy = hits / moves if moves > 0 else 0

        difficulty_factor = 1

        if final_speed < 1000:
            difficulty_factor = 1.5
        elif final_speed < 1500:
            difficulty_factor = 1.2
        else:
            difficulty_factor = 1

        if duration > 0:
            speed_score = min(1, 10 / duration)
        else:
            speed_score = 0

        final_score = (accuracy * 0.6) + (speed_score * 0.4)
        score = round(final_score * 100 * difficulty_factor)
        errors = moves - hits if moves >= hits else 0
        # === SYSTEM ACTION CALCULATION ===
        system_action = 'Keep Current Level'

        if final_speed > 2000 and score < 40:
            system_action = 'Reduce Difficulty'

        elif score < 60:
            system_action = ' Monitor Closely'

        elif final_speed <= 1200 and score > 70:
            system_action = 'Increase Difficulty'

        print('SAVE SYSTEM ACTION:', system_action)

        session = GameSession.objects.create(
            child=child,
            game_type='follow_star',
            duration_seconds=duration
        )
        alert_triggered = False

        if score < 40 or final_speed < 1000:
            alert_triggered = True
            print('ALERT TRIGGGERED ', alert_triggered)

        if alert_triggered:
            print('sending SMS...')
            send_sms_alert(
                to_number='+19166802487',
                message=f'Alert: Your child may need support. Score: {score}. Action: {system_action}'

            )

        metrics = Metrics.objects.create(
            session=session,
            accuracy=accuracy,
            reaction_time=0,
            errors=errors,
            score=score,
            final_speed=final_speed,
            system_action=system_action,
            alert_triggered=alert_triggered,

        )
        if alert_triggered:
            Alert.objects.create(
                child=child,
                session=session,
                message='Child may be struggling. Consider Intervention.',
                system_action=system_action,
                score=score,
                sent_sms=False,
            )

        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'invalid request'}, status=400)


def privacy_view(request):
    return render(request, 'core/privacy.html')


def terms_view(request):
    return render(request, 'core/terms.html')


def send_sms_alert(to_number, message):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    client.messages.create(
        body=message,
        from_=settings.TWILIO_PHONE_NUMBER,
        to=to_number
    )


def send_sms_alert(to_number, message):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    try:
        message = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to_number
        )
        print('SMS SENT:', message.sid)

    except Exception as e:
        print('SMS ERROR:', str(e))
