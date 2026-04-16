import os
import json
import requests
from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from .models import TranslationHistory, RateLimitSetting

def get_client_ip(request):
    """Get the client's real IP address from headers."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def is_rate_limited(request):
    """
    Check if a user (or guest IP) has exceeded the global rate limit.
    Admins (is_staff) are exempt.
    """
    user = request.user
    
    # Admins are never limited
    if user.is_authenticated and user.is_staff:
        return False, None
    
    # Get global setting
    setting = RateLimitSetting.objects.first()
    if not setting or not setting.enabled:
        return False, None
    
    # Calculate window start
    window_start = timezone.now() - timedelta(hours=setting.window_hours)
    
    # Logic:
    # 1. If Authenticated: Check by user ID.
    # 2. If Guest: Check by IP address among entries where user is null.
    if user.is_authenticated:
        filter_q = Q(user=user)
    else:
        client_ip = get_client_ip(request)
        # Note: We filter for entries with this IP where user IS NULL.
        # This prevents a logged-in user from being double-counted if they 
        # use the same IP as a guest, but the guest limit remains strictly per-IP.
        filter_q = Q(ip_address=client_ip, user__isnull=True)

    request_count = TranslationHistory.objects.filter(
        filter_q,
        created_at__gte=window_start
    ).count()
    
    if request_count >= setting.max_requests:
        return True, setting
    
    return False, None

def index(request):
    input_text = ""
    translated_text = ""
    direction = "en-tw"
    
    if request.method == 'POST':
        input_text = request.POST.get('text', '')
        direction = request.POST.get('direction', 'en-tw')
        
        if input_text:
            try:
                # 1. Check Rate Limit
                limited, setting = is_rate_limited(request)
                if limited:
                    raise Exception(f"Rate limit exceeded. You can only make {setting.max_requests} requests every {setting.window_hours} hour(s).")

                # 2. Check API Key
                api_key = os.environ.get('GHANA_NLP_API_KEY')
                if not api_key:
                    raise Exception("Translation API key is missing. Please configure your .env file.")

                # 3. Perform Translation
                url = "https://translation-api.ghananlp.org/v1/translate"
                headers = {
                    'Content-Type': 'application/json',
                    'Ocp-Apim-Subscription-Key': api_key,
                }
                payload = {"in": input_text, "lang": direction}
                
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                response.raise_for_status()
                
                try:
                    res_data = response.json()
                    translated_text = res_data.get('out', str(res_data))
                except (ValueError, AttributeError):
                    translated_text = response.text.strip(' \n"')

                # 4. Save to History (Guest or User)
                TranslationHistory.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    source_text=input_text,
                    translated_text=translated_text,
                    direction=direction,
                    ip_address=get_client_ip(request)
                )
            except Exception as e:
                from django.contrib import messages
                messages.error(request, f"Translation failed: {str(e)}")

    db_history = []
    if request.user.is_authenticated:
        db_history = TranslationHistory.objects.filter(user=request.user).order_by('-created_at')[:50]
    else:
        # For guests, show only their recent local session history (by IP)
        client_ip = get_client_ip(request)
        db_history = TranslationHistory.objects.filter(ip_address=client_ip, user__isnull=True).order_by('-created_at')[:10]
        
    context = {
        'db_history': db_history,
        'input_text': input_text,
        'translated_text': translated_text,
        'direction': direction,
    }
    return render(request, 'core/index.html', context)

def translate_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # 1. Check Rate Limit
        limited, setting = is_rate_limited(request)
        if limited:
            return JsonResponse({
                'error': f'Rate limit exceeded. You can only make {setting.max_requests} requests every {setting.window_hours} hour(s).'
            }, status=429)

        data = json.loads(request.body)
        text = data.get('text', '')
        direction = data.get('direction', 'en-tw')
        
        if not text:
            return JsonResponse({'error': 'No text provided'}, status=400)

        api_key = os.environ.get('GHANA_NLP_API_KEY')
        url = "https://translation-api.ghananlp.org/v1/translate"
        headers = {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            'Ocp-Apim-Subscription-Key': api_key,
        }
        payload = {
            "in": text,
            "lang": direction
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        try:
            translated_text = response.json()
        except ValueError:
            translated_text = response.text.strip(' \n"')
            
        if isinstance(translated_text, dict):
            translated_text = translated_text.get('out', str(translated_text))

        # Always Record History
        TranslationHistory.objects.create(
            user=request.user if request.user.is_authenticated else None,
            source_text=text,
            translated_text=translated_text,
            direction=direction,
            ip_address=get_client_ip(request)
        )

        return JsonResponse({'result': translated_text})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
