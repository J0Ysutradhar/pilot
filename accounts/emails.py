"""
Email helper functions for Page Pilot.
Sends HTML emails for welcome, KYC, and subscription events.
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def _send_email(subject, template_name, context, recipient_email):
    """
    Internal helper — renders an HTML template and sends it.
    Silently logs errors so email failures never break the app.
    """
    try:
        context.setdefault('site_url', settings.SITE_URL)
        context.setdefault('site_name', settings.SITE_NAME)

        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        msg.attach_alternative(html_content, 'text/html')
        msg.send(fail_silently=False)
        logger.info(f'Email sent: "{subject}" → {recipient_email}')
        return True
    except Exception as e:
        logger.error(f'Email failed: "{subject}" → {recipient_email}: {e}')
        return False


def send_welcome_email(user):
    """Send welcome email after successful registration."""
    return _send_email(
        subject=f'Welcome to {settings.SITE_NAME}! 🚀',
        template_name='emails/welcome.html',
        context={
            'user_name': getattr(user, 'get_full_name', lambda: user.email)() or user.email,
            'email': user.email,
        },
        recipient_email=user.email,
    )


def send_kyc_approved_email(profile):
    """Send email when KYC is approved."""
    return _send_email(
        subject=f'KYC Verified — You\'re All Set! ✅',
        template_name='emails/kyc_approved.html',
        context={
            'user_name': profile.name or profile.user.email,
        },
        recipient_email=profile.user.email,
    )


def send_kyc_rejected_email(profile):
    """Send email when KYC is rejected, including the reason."""
    return _send_email(
        subject=f'KYC Submission Update — Action Required',
        template_name='emails/kyc_rejected.html',
        context={
            'user_name': profile.name or profile.user.email,
            'rejection_reason': profile.kyc_rejection_reason or 'No specific reason provided.',
        },
        recipient_email=profile.user.email,
    )


def send_subscription_expiry_warning(profile, days_remaining):
    """Send subscription expiry warning email."""
    return _send_email(
        subject=f'Your {settings.SITE_NAME} Subscription Expires in {days_remaining} Day{"s" if days_remaining != 1 else ""}',
        template_name='emails/subscription_expiry.html',
        context={
            'user_name': profile.name or profile.user.email,
            'days_remaining': days_remaining,
            'expiry_date': profile.subscription_expiry,
            'package_name': profile.package_name or 'Your Plan',
        },
        recipient_email=profile.user.email,
    )


def send_payment_approved_email(payment_request):
    """Send email when a payment request is approved."""
    profile = payment_request.user.profile
    return _send_email(
        subject=f'Payment Approved — Subscription Upgraded! 🎉',
        template_name='emails/payment_approved.html',
        context={
            'user_name': profile.name or profile.user.email,
            'package_name': payment_request.package_name,
            'amount': payment_request.amount,
        },
        recipient_email=profile.user.email,
    )


def send_payment_rejected_email(payment_request):
    """Send email when a payment request is rejected."""
    profile = payment_request.user.profile
    return _send_email(
        subject=f'Payment Rejected — Action Required',
        template_name='emails/payment_rejected.html',
        context={
            'user_name': profile.name or profile.user.email,
            'package_name': payment_request.package_name,
            'amount': payment_request.amount,
        },
        recipient_email=profile.user.email,
    )
