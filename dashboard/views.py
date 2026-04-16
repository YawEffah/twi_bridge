from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta
from core.models import TranslationHistory, RateLimitSetting
from .decorators import staff_required


# ─────────────────────────────────────────────
#  SETTINGS — Global app settings
# ─────────────────────────────────────────────
@staff_required
def settings_view(request):
    # Get or create the single settings instance
    setting = RateLimitSetting.objects.first()
    if not setting:
        setting = RateLimitSetting.objects.create()

    if request.method == 'POST':
        max_reqs = request.POST.get('max_requests')
        window   = request.POST.get('window_hours')
        enabled  = request.POST.get('enabled') == 'on'

        try:
            setting.max_requests = int(max_reqs)
            setting.window_hours = int(window)
            setting.enabled      = enabled
            setting.save()
            messages.success(request, "System settings updated successfully.")
        except ValueError:
            messages.error(request, "Invalid input. Please enter numbers for the limits.")
        
        return redirect('dashboard_settings')

    return render(request, 'dashboard/settings.html', {'setting': setting})


# ─────────────────────────────────────────────
#  OVERVIEW — Stats dashboard
# ─────────────────────────────────────────────
@staff_required
def overview(request):
    now = timezone.now()
    week_ago  = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users        = User.objects.count()
    total_translations = TranslationHistory.objects.count()
    week_translations  = TranslationHistory.objects.filter(created_at__gte=week_ago).count()
    month_translations = TranslationHistory.objects.filter(created_at__gte=month_ago).count()
    new_users_week     = User.objects.filter(date_joined__gte=week_ago).count()
    active_users       = User.objects.filter(is_active=True).count()
    staff_users        = User.objects.filter(is_staff=True).count()

    # Direction split
    en_tw_count = TranslationHistory.objects.filter(direction='en-tw').count()
    tw_en_count = TranslationHistory.objects.filter(direction='tw-en').count()

    # Top 5 most active users
    top_users = (
        User.objects
        .annotate(t_count=Count('translationhistory'))
        .filter(t_count__gt=0)
        .order_by('-t_count')[:5]
    )

    # Daily breakdown for the last 7 days
    daily_stats = []
    for i in range(6, -1, -1):
        day_start = now - timedelta(days=i+1)
        day_end   = now - timedelta(days=i)
        count = TranslationHistory.objects.filter(
            created_at__gte=day_start, created_at__lt=day_end
        ).count()
        daily_stats.append({
            'label': day_start.strftime('%b %d'),
            'count': count,
        })

    # Recent 5 translations
    recent_translations = TranslationHistory.objects.select_related('user').order_by('-created_at')[:5]

    context = {
        'total_users':        total_users,
        'total_translations': total_translations,
        'week_translations':  week_translations,
        'month_translations': month_translations,
        'new_users_week':     new_users_week,
        'active_users':       active_users,
        'staff_users':        staff_users,
        'en_tw_count':        en_tw_count,
        'tw_en_count':        tw_en_count,
        'top_users':          top_users,
        'daily_stats':        daily_stats,
        'recent_translations':recent_translations,
    }
    return render(request, 'dashboard/overview.html', context)


# ─────────────────────────────────────────────
#  USERS — Searchable paginated user table
# ─────────────────────────────────────────────
@staff_required
def users(request):
    from django.core.paginator import Paginator

    search_q = request.GET.get('q', '').strip()
    filter_status = request.GET.get('status', '')  # 'active' | 'inactive' | 'staff'

    qs = User.objects.annotate(t_count=Count('translationhistory')).order_by('-date_joined')

    if search_q:
        qs = qs.filter(
            Q(username__icontains=search_q) |
            Q(email__icontains=search_q) |
            Q(first_name__icontains=search_q) |
            Q(last_name__icontains=search_q)
        )

    if filter_status == 'active':
        qs = qs.filter(is_active=True, is_staff=False)
    elif filter_status == 'inactive':
        qs = qs.filter(is_active=False)
    elif filter_status == 'staff':
        qs = qs.filter(is_staff=True)

    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj':     page_obj,
        'search_q':     search_q,
        'filter_status':filter_status,
        'total_count':  qs.count(),
    }
    return render(request, 'dashboard/users.html', context)


# ─────────────────────────────────────────────
#  USER DETAIL — Single user + history + actions
# ─────────────────────────────────────────────
@staff_required
def user_detail(request, user_id):
    from django.core.paginator import Paginator

    target = get_object_or_404(User, pk=user_id)
    history_qs = TranslationHistory.objects.filter(user=target).order_by('-created_at')

    paginator = Paginator(history_qs, 15)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    en_tw = history_qs.filter(direction='en-tw').count()
    tw_en = history_qs.filter(direction='tw-en').count()

    context = {
        'target':    target,
        'page_obj':  page_obj,
        'en_tw':     en_tw,
        'tw_en':     tw_en,
        'total_t':   history_qs.count(),
    }
    return render(request, 'dashboard/user_detail.html', context)


# ─────────────────────────────────────────────
#  USER ACTION — POST-only, performs user mutations
# ─────────────────────────────────────────────
@staff_required
def user_action(request, user_id):
    if request.method != 'POST':
        return redirect('dashboard_users')

    target = get_object_or_404(User, pk=user_id)
    action = request.POST.get('action', '')

    # Prevent admins from acting on themselves
    if target == request.user and action in ('suspend', 'remove_staff', 'delete'):
        messages.error(request, "You cannot perform this action on your own account.")
        return redirect('dashboard_user_detail', user_id=user_id)

    if action == 'suspend':
        target.is_active = False
        target.save()
        messages.success(request, f"{target.username} has been suspended.")

    elif action == 'activate':
        target.is_active = True
        target.save()
        messages.success(request, f"{target.username} has been activated.")

    elif action == 'make_staff':
        target.is_staff = True
        target.save()
        messages.success(request, f"{target.username} has been granted staff access.")

    elif action == 'remove_staff':
        target.is_staff = False
        target.save()
        messages.success(request, f"Staff access removed from {target.username}.")

    elif action == 'delete':
        username = target.username
        target.delete()
        messages.success(request, f"User '{username}' and all their data have been deleted.")
        return redirect('dashboard_users')

    else:
        messages.error(request, "Unknown action.")

    return redirect('dashboard_user_detail', user_id=user_id)


# ─────────────────────────────────────────────
#  TRANSLATIONS — Global activity feed
# ─────────────────────────────────────────────
@staff_required
def translations(request):
    from django.core.paginator import Paginator

    direction_filter = request.GET.get('direction', '')
    date_filter      = request.GET.get('date', '')
    search_q         = request.GET.get('q', '').strip()

    qs = TranslationHistory.objects.select_related('user').order_by('-created_at')

    if direction_filter in ('en-tw', 'tw-en'):
        qs = qs.filter(direction=direction_filter)

    if date_filter == 'today':
        qs = qs.filter(created_at__date=timezone.now().date())
    elif date_filter == 'week':
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=7))
    elif date_filter == 'month':
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=30))

    if search_q:
        qs = qs.filter(
            Q(source_text__icontains=search_q) |
            Q(translated_text__icontains=search_q) |
            Q(user__username__icontains=search_q) |
            Q(ip_address__icontains=search_q)
        )

    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_obj':         page_obj,
        'direction_filter': direction_filter,
        'date_filter':      date_filter,
        'search_q':         search_q,
        'total_count':      qs.count(),
    }
    return render(request, 'dashboard/translations.html', context)
