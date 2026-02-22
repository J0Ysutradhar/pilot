from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
import json
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.core.paginator import Paginator
from .models import CustomUser, UserProfile, AIAgentConfig, PaymentRequest

# Check if user is superuser
def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser)
def admin_dashboard(request):
    """
    Main Admin Dashboard View
    Displays overview statistics and recent activity.
    """
    total_users = CustomUser.objects.count()
    new_users_today = CustomUser.objects.filter(date_joined__date=timezone.now().date()).count()
    pending_kyc = UserProfile.objects.filter(kyc_status='PENDING').count()
    pending_payments = PaymentRequest.objects.filter(status='PENDING').count()
    total_ai_agents = AIAgentConfig.objects.count()
    
    # Recent 5 users
    recent_users = CustomUser.objects.select_related('profile').order_by('-date_joined')[:5]

    context = {
        'total_users': total_users,
        'new_users_today': new_users_today,
        'pending_kyc': pending_kyc,
        'pending_payments': pending_payments,
        'total_ai_agents': total_ai_agents,
        'recent_users': recent_users,
        'active_subscriptions': UserProfile.objects.filter(subscription_expiry__gt=timezone.now()).count()
    }
    return render(request, 'custom_admin/dashboard.html', context)


@login_required
@user_passes_test(is_superuser)
def admin_user_list(request):
    """
    List all users with search, filtering, and pagination
    """
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'all')
    
    users = CustomUser.objects.select_related('profile').all().order_by('-date_joined')
    
    if query:
        users = users.filter(
            Q(email__icontains=query) | 
            Q(profile__name__icontains=query) |
            Q(profile__mobile_number__icontains=query)
        )
        
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    elif status_filter == 'verified':
        users = users.filter(profile__kyc_status='VERIFIED')
    elif status_filter == 'pending':
        users = users.filter(profile__kyc_status='PENDING')

    # Pagination — 20 users per page
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'users': page_obj,
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter
    }
    return render(request, 'custom_admin/user_list.html', context)


@login_required
@user_passes_test(is_superuser)
def admin_user_detail(request, user_id):
    """
    View to manage a specific user
    """
    user = get_object_or_404(CustomUser, id=user_id)
    profile = user.profile
    ai_config = getattr(user, 'ai_config', None)
    payment_requests = PaymentRequest.objects.filter(user=user).order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'toggle_status':
            user.is_active = not user.is_active
            user.save()
            messages.success(request, f"User status updated to {'Active' if user.is_active else 'Inactive'}.")
            
        elif action == 'assign_subscription':
            days = int(request.POST.get('days', 0))
            if days > 0:
                profile.subscription_expiry = timezone.now() + timezone.timedelta(days=days)
                profile.package_name = f"{days} Days Package"
                profile.save()
                
                # Log history
                from .models import SubscriptionHistory
                SubscriptionHistory.objects.create(
                    profile=profile,
                    package_name=f"{days} Days Package - Admin Assigned",
                    expiry_date=profile.subscription_expiry
                )
                
                messages.success(request, f"Subscription extended by {days} days.")
        
        elif action == 'update_info':
             profile.name = request.POST.get('name', profile.name)
             profile.mobile_number = request.POST.get('mobile_number', profile.mobile_number)
             user.email = request.POST.get('email', user.email)
             profile.save()
             user.save()
             messages.success(request, "User information updated.")

        return redirect('admin_user_detail', user_id=user_id)
        
    context = {
        'user_obj': user,
        'profile': profile,
        'ai_config': ai_config,
        'payment_requests': payment_requests,
    }
    return render(request, 'custom_admin/user_detail.html', context)


@login_required
@user_passes_test(is_superuser)
def admin_kyc_list(request):
    """
    List pending KYC requests
    """
    kyc_requests = UserProfile.objects.filter(
        kyc_status='PENDING'
    ).select_related('user').order_by('-user__date_joined')
    
    context = {
        'kyc_requests': kyc_requests
    }
    return render(request, 'custom_admin/kyc_list.html', context)


@login_required
@user_passes_test(is_superuser)
def admin_kyc_action(request):
    """
    Handle KYC Approval/rejection with optional rejection reason
    """
    profile = None
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        profile = get_object_or_404(UserProfile, user__id=user_id)
#https://github.com/J0Ysutradhar/pilot.git
        if action == 'approve':
            profile.kyc_status = 'VERIFIED'
            profile.kyc_rejection_reason = ''  # Clear any previous rejection reason
            profile.save()
            from .emails import send_kyc_approved_email
            send_kyc_approved_email(profile)
            messages.success(request, f"KYC for {profile.user.email} has been APPROVED.")
            
        elif action == 'reject':
            rejection_reason = request.POST.get('rejection_reason', '').strip()
            profile.kyc_status = 'REJECTED'
            profile.kyc_rejection_reason = rejection_reason or 'Your KYC submission did not meet our requirements. Please re-submit with clear images.'
            profile.save()
            from .emails import send_kyc_rejected_email
            send_kyc_rejected_email(profile)
            messages.warning(request, f"KYC for {profile.user.email} has been REJECTED.")
            
    return redirect('admin_kyc_list')


@login_required
@user_passes_test(is_superuser)
def admin_subscription_list(request):
    """
    Subscription Management Page — view and manage all user subscriptions
    """
    now = timezone.now()
    status_filter = request.GET.get('status', 'all')
    query = request.GET.get('q', '')

    profiles = UserProfile.objects.select_related('user').all().order_by('-subscription_expiry')

    # Stats
    total_active = UserProfile.objects.filter(subscription_expiry__gt=now).count()
    expiring_soon = UserProfile.objects.filter(
        subscription_expiry__gt=now,
        subscription_expiry__lte=now + timezone.timedelta(days=7)
    ).count()
    total_expired = UserProfile.objects.filter(subscription_expiry__lte=now).count()
    never_subscribed = UserProfile.objects.filter(subscription_expiry__isnull=True).count()

    # Search
    if query:
        profiles = profiles.filter(
            Q(user__email__icontains=query) |
            Q(name__icontains=query) |
            Q(mobile_number__icontains=query)
        )

    # Filter
    if status_filter == 'active':
        profiles = profiles.filter(subscription_expiry__gt=now)
    elif status_filter == 'expired':
        profiles = profiles.filter(subscription_expiry__lte=now)
    elif status_filter == 'expiring_soon':
        profiles = profiles.filter(
            subscription_expiry__gt=now,
            subscription_expiry__lte=now + timezone.timedelta(days=7)
        )
    elif status_filter == 'never':
        profiles = profiles.filter(subscription_expiry__isnull=True)

    # Pagination
    paginator = Paginator(profiles, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Handle quick subscription extend from this page
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        days = int(request.POST.get('days', 0))
        if user_id and days > 0:
            target_profile = get_object_or_404(UserProfile, user__id=user_id)
            if target_profile.subscription_expiry and target_profile.subscription_expiry > now:
                # Extend from current expiry
                target_profile.subscription_expiry = target_profile.subscription_expiry + timezone.timedelta(days=days)
            else:
                # Start fresh from now
                target_profile.subscription_expiry = now + timezone.timedelta(days=days)
            target_profile.package_name = f"{days} Days Package"
            target_profile.save()

            from .models import SubscriptionHistory
            SubscriptionHistory.objects.create(
                profile=target_profile,
                package_name=f"{days} Days Package - Admin Assigned",
                expiry_date=target_profile.subscription_expiry
            )
            messages.success(request, f"Subscription for {target_profile.user.email} extended by {days} days.")
            return redirect(f"{request.path}?status={status_filter}&q={query}")

    context = {
        'profiles': page_obj,
        'page_obj': page_obj,
        'total_active': total_active,
        'expiring_soon': expiring_soon,
        'total_expired': total_expired,
        'never_subscribed': never_subscribed,
        'status_filter': status_filter,
        'query': query,
    }
    return render(request, 'custom_admin/subscription_list.html', context)


@login_required
@user_passes_test(is_superuser)
def admin_payment_list(request):
    """
    List user Payment Requests for review.
    """
    status_filter = request.GET.get('status', 'PENDING')
    query = request.GET.get('q', '')

    payments = PaymentRequest.objects.select_related('user').all().order_by('-created_at')

    if status_filter != 'all':
        payments = payments.filter(status=status_filter.upper())
        
    if query:
        payments = payments.filter(
            Q(user__email__icontains=query) |
            Q(transaction_id__icontains=query)
        )

    # Stats
    pending_count = PaymentRequest.objects.filter(status='PENDING').count()
    approved_count = PaymentRequest.objects.filter(status='APPROVED').count()

    paginator = Paginator(payments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'payments': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'query': query,
        'pending_count': pending_count,
        'approved_count': approved_count
    }
    return render(request, 'custom_admin/payment_list.html', context)


@login_required
@user_passes_test(is_superuser)
def admin_payment_action(request):
    """
    Handle Approve/Reject for Payment Requests
    """
    if request.method == 'POST':
        payment_id = request.POST.get('payment_id')
        action = request.POST.get('action')
        
        payment = get_object_or_404(PaymentRequest, id=payment_id)
        
        # Prevent double-processing
        if payment.status != 'PENDING':
            messages.warning(request, f"Payment {payment.transaction_id} was already processed.")
            return redirect('admin_payment_list')

        if action == 'approve':
            from django.utils import timezone
            from datetime import timedelta
            from .models import SubscriptionHistory
            from .emails import send_payment_approved_email

            payment.status = 'APPROVED'
            payment.save()

            now = timezone.now()
            profile = payment.user.profile
            days = 0
            if '15' in payment.package_name:
                days = 15
            elif '30' in payment.package_name:
                days = 30
            
            if days > 0:
                if profile.subscription_expiry and profile.subscription_expiry > now:
                    new_expiry = profile.subscription_expiry + timedelta(days=days)
                else:
                    new_expiry = now + timedelta(days=days)
                
                profile.subscription_expiry = new_expiry
                profile.package_name = payment.package_name
                profile.save(update_fields=['subscription_expiry', 'package_name'])
                
                SubscriptionHistory.objects.create(
                    profile=profile,
                    package_name=payment.package_name,
                    expiry_date=new_expiry
                )
            
            send_payment_approved_email(payment)
            messages.success(request, f"Payment for {payment.user.email} APPROVED. Subscription extended.")
            
        elif action == 'reject':
            from .emails import send_payment_rejected_email
            payment.status = 'REJECTED'
            payment.save()
            send_payment_rejected_email(payment)
            messages.warning(request, f"Payment for {payment.user.email} REJECTED.")
            
    return redirect('admin_payment_list')


@login_required
@user_passes_test(is_superuser)
def admin_analytics(request):
    """
    Analytics and Revenue Dashboard
    """
    now = timezone.now()
    thirty_days_ago = now - timezone.timedelta(days=30)
    
    # 1. Total Revenue (from approved payments all time)
    total_revenue = PaymentRequest.objects.filter(status='APPROVED').aggregate(total=Sum('amount'))['total'] or 0
    
    # 2. Daily User Growth (last 30 days)
    daily_users = CustomUser.objects.filter(date_joined__gte=thirty_days_ago) \
        .annotate(date=TruncDate('date_joined')) \
        .values('date') \
        .annotate(count=Count('id')) \
        .order_by('date')
    
    dates_users = [item['date'].strftime('%b %d') for item in daily_users]
    counts_users = [item['count'] for item in daily_users]
    
    # 3. Revenue Over Time (last 30 days)
    daily_revenue = PaymentRequest.objects.filter(status='APPROVED', created_at__gte=thirty_days_ago) \
        .annotate(date=TruncDate('created_at')) \
        .values('date') \
        .annotate(total=Sum('amount')) \
        .order_by('date')
        
    dates_revenue = [item['date'].strftime('%b %d') for item in daily_revenue]
    amounts_revenue = [float(item['total']) for item in daily_revenue]
    
    # 4. KYC Conversion
    kyc_stats = UserProfile.objects.values('kyc_status').annotate(count=Count('id'))
    kyc_labels = []
    kyc_data = []
    for stat in kyc_stats:
        status = stat['kyc_status']
        if not status: status = 'UNVERIFIED'
        kyc_labels.append(status)
        kyc_data.append(stat['count'])
        
    # 5. Subscriptions by Package (Active)
    package_stats = UserProfile.objects.filter(subscription_expiry__gt=now) \
        .values('package_name') \
        .annotate(count=Count('id'))
    
    package_labels = []
    package_data = []
    for stat in package_stats:
        name = stat['package_name']
        if not name: name = 'Free Trial'
        package_labels.append(name)
        package_data.append(stat['count'])
        
    context = {
        'total_revenue': total_revenue,
        'dates_users_json': json.dumps(dates_users),
        'counts_users_json': json.dumps(counts_users),
        'dates_revenue_json': json.dumps(dates_revenue),
        'amounts_revenue_json': json.dumps(amounts_revenue),
        'kyc_labels_json': json.dumps(kyc_labels),
        'kyc_data_json': json.dumps(kyc_data),
        'package_labels_json': json.dumps(package_labels),
        'package_data_json': json.dumps(package_data),
    }
    
    return render(request, 'custom_admin/analytics.html', context)
