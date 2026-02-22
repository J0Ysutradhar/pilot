from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse, Http404
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm, AIAgentConfigForm, KYCUploadForm

from .models import CustomUser, UserProfile, AIAgentConfig
import pandas as pd
import io
import requests



from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@login_required
def report_view(request):
    """Fetch and display report from Google Sheet"""
    # Ensure AI config exists
    ai_config, created = AIAgentConfig.objects.get_or_create(user=request.user)
    
    # Handle Sheet ID update
    if request.method == 'POST' and 'google_sheet_id' in request.POST:
        new_id = request.POST.get('google_sheet_id', '').strip()
        if new_id:
            ai_config.google_sheet_id = new_id
            ai_config.save()
            messages.success(request, 'Report ID updated successfully!')
            return redirect('report')
            
    sheet_id = ai_config.google_sheet_id
    
    data = []
    columns = []
    error = None
    page_obj = None
    
    if sheet_id:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            # Read into pandas DataFrame with UTF-8 encoding
            # Use content (bytes) and BytesIO for better encoding handling
            df = pd.read_csv(io.BytesIO(response.content), encoding='utf-8')
            
            # Filter logic if requested
            query = request.GET.get('q', '').strip()
            if query:
                # Simple case-insensitive search across all columns
                mask = df.astype(str).apply(lambda x: x.str.contains(query, case=False, na=False)).any(axis=1)
                df = df[mask]
                

            columns = df.columns.tolist()
            df = df.iloc[::-1] # Reverse payload to show most recent at top
            df = df.fillna('') # Replace NaN with empty string
            
            # Handle Excel Download
            if request.GET.get('download') == 'true':
                from django.http import HttpResponse
                
                # Create Excel file in memory
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Report')
                
                excel_buffer.seek(0)
                response = HttpResponse(excel_buffer.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename="report.xlsx"'
                return response
            
            data_list = df.values.tolist()
            
            # Pagination
            paginator = Paginator(data_list, 20) # Show 20 contacts per page
            page_number = request.GET.get('page')
            try:
                page_obj = paginator.get_page(page_number)
            except PageNotAnInteger:
                page_obj = paginator.get_page(1)
            except EmptyPage:
                page_obj = paginator.get_page(paginator.num_pages)
                
            data = page_obj # For template compatibility if needed, but we'll use page_obj
            
        except Exception as e:
            error = f"Failed to load report data: {str('Invalid Report ID, Please Check and try again or contact support. +8801781763345')}"
    
    return render(request, 'accounts/report.html', {
        'data': page_obj if page_obj else data, # Pass page_obj as data to keep template loop working or explicit page_obj
        'page_obj': page_obj,
        'columns': columns,
        'error': error,
        'query': request.GET.get('q', ''),
        'google_sheet_id': sheet_id
    })


@login_required
def report_data_api(request):
    """JSON API endpoint for auto-refreshing report table data"""
    from django.http import JsonResponse

    ai_config, _ = AIAgentConfig.objects.get_or_create(user=request.user)
    sheet_id = ai_config.google_sheet_id

    if not sheet_id:
        return JsonResponse({'error': 'No sheet ID configured'}, status=400)

    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        response = requests.get(url)
        response.raise_for_status()

        df = pd.read_csv(io.BytesIO(response.content), encoding='utf-8')

        query = request.GET.get('q', '').strip()
        if query:
            mask = df.astype(str).apply(lambda x: x.str.contains(query, case=False, na=False)).any(axis=1)
            df = df[mask]

        columns = df.columns.tolist()
        df = df.iloc[::-1]
        df = df.fillna('')
        data_list = df.values.tolist()

        # Pagination
        page_number = int(request.GET.get('page', 1))
        per_page = 20
        total_pages = max(1, (len(data_list) + per_page - 1) // per_page)
        page_number = min(page_number, total_pages)
        start = (page_number - 1) * per_page
        end = start + per_page
        page_data = data_list[start:end]

        return JsonResponse({
            'columns': columns,
            'data': page_data,
            'page': page_number,
            'total_pages': total_pages,
            'total_records': len(data_list),
            'has_previous': page_number > 1,
            'has_next': page_number < total_pages,
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



def register_view(request):
    """Handle user registration"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            full_name = form.cleaned_data.get('full_name', '')
            phone_number = form.cleaned_data.get('phone_number', '')
            user.first_name = full_name
            user.save()
            # Create associated profile and AI config
            UserProfile.objects.create(user=user, name=full_name, mobile_number=phone_number)
            AIAgentConfig.objects.create(user=user)
            # Send welcome email
            # from .emails import send_welcome_email
            # send_welcome_email(user)
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
            from .emails import send_welcome_email
            send_welcome_email(user)
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """Handle user login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {email}!')
                return redirect('dashboard')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Handle user logout"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


@login_required
def dashboard_view(request):
    """Display user dashboard"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    ai_config, _ = AIAgentConfig.objects.get_or_create(user=request.user)

    context = {
        'user': request.user,
        'profile': profile,
        'ai_config': ai_config,
    }
    return render(request, 'accounts/dashboard.html', context)


@login_required
def profile_view(request):
    """Display and update user profile"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        if 'kyc_submit' in request.POST:
            # Handle KYC document upload
            kyc_form = KYCUploadForm(request.POST, request.FILES, instance=profile)
            if not profile.is_profile_complete():
                messages.error(request, 'Please complete your profile information before submitting KYC.')
                return redirect('profile')

            if kyc_form.is_valid():
                kyc_profile = kyc_form.save(commit=False)
                kyc_profile.kyc_status = 'PENDING'
                kyc_profile.save()
                messages.success(request, 'KYC document submitted successfully! Your verification is under review.')
                return redirect('profile')
            form = UserProfileForm(instance=profile)
        else:
            # Handle profile update
            form = UserProfileForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('profile')
            kyc_form = KYCUploadForm(instance=profile)
    else:
        form = UserProfileForm(instance=profile)
    
    kyc_form = KYCUploadForm(instance=profile)
    
    return render(request, 'accounts/profile.html', {
        'form': form,
        'kyc_form': kyc_form,
        'profile': profile
    })


def privacy_policy_view(request, email_prefix):
    """Public privacy policy page for a user based on their email prefix"""
    try:
        user = CustomUser.objects.get(email__startswith=email_prefix + '@')
    except CustomUser.DoesNotExist:
        try:
            user = CustomUser.objects.get(email=email_prefix)
        except CustomUser.DoesNotExist:
            from django.http import Http404
            raise Http404("Privacy policy page not found.")

    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        from django.http import Http404
        raise Http404("Privacy policy page not found.")

    if not profile.business_info:
        from django.http import Http404
        raise Http404("Privacy policy page not found.")

    return render(request, 'accounts/privacy_policy.html', {
        'profile': profile,
        'page_user': user,
    })


@login_required
def ai_agent_view(request):
    """Display and update AI agent configuration"""
    # KYC verification check
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.kyc_status != 'VERIFIED':
        return redirect('kyc_required')
    
    ai_config, created = AIAgentConfig.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = AIAgentConfigForm(request.POST, instance=ai_config)
        if form.is_valid():
            form.save()
            
            # Handle AJAX request for auto-save
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Variable saved'})
                
            messages.success(request, 'AI Agent configuration saved successfully!')
            return redirect('ai_agent')
        
        # Handle AJAX errors
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    else:
        form = AIAgentConfigForm(instance=ai_config)
    
    webhook_url = ai_config.get_webhook_url()
    
    # Check subscription status
    subscription_active = True
    if profile:
        subscription_active = profile.is_subscription_active()

    return render(request, 'accounts/ai_agent.html', {
        'form': form,
        'webhook_url': webhook_url,
        'ai_config': ai_config,
        'subscription_active': subscription_active
    })


@login_required
def feed_view(request):
    """Display Facebook Page feed (posts) using the Graph API"""
    page_name = None
    posts = []
    error = None

    try:
        ai_config = AIAgentConfig.objects.get(user=request.user)
        page_id = ai_config.facebook_page_id
        access_token = ai_config.facebook_page_api

        if not page_id or not access_token:
            error = 'Facebook Page ID or API key is missing. Please configure your AI Agent first.'
        else:
            # Fetch page name
            try:
                name_resp = requests.get(
                    f"https://graph.facebook.com/v24.0/{page_id}",
                    params={'fields': 'name', 'access_token': access_token}
                )
                if name_resp.status_code == 200:
                    page_name = name_resp.json().get('name', 'Unknown Page')
            except Exception:
                page_name = 'Unknown Page'

            # Fetch page feed
            feed_resp = requests.get(
                f"https://graph.facebook.com/v24.0/{page_id}/feed",
                params={'access_token': access_token, 'fields': 'id,message,created_time,full_picture,permalink_url'}
            )

            if feed_resp.status_code == 200:
                feed_data = feed_resp.json()
                posts = feed_data.get('data', [])
            else:
                err_data = feed_resp.json()
                error = err_data.get('error', {}).get('message', 'Failed to fetch feed.')

    except AIAgentConfig.DoesNotExist:
        error = 'AI Agent configuration not found. Please set it up first.'
    except Exception as e:
        error = f'An error occurred: {str(e)}'

    return render(request, 'accounts/feed.html', {
        'page_name': page_name,
        'posts': posts,
        'error': error,
    })


@login_required
def create_post_view(request):
    """Create a post on the user's Facebook Page using the Graph API"""
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        image = request.FILES.get('image')

        if not message and not image:
            messages.error(request, 'Please provide a message or an image for the post.')
            return redirect('feed')

        try:
            ai_config = AIAgentConfig.objects.get(user=request.user)
            page_id = ai_config.facebook_page_id
            access_token = ai_config.facebook_page_api

            if not page_id or not access_token:
                messages.error(request, 'Facebook Page ID or API key is missing. Please configure your AI Agent first.')
                return redirect('ai_agent')

            if image:
                # Photo post: POST /{page_id}/photos
                url = f"https://graph.facebook.com/v24.0/{page_id}/photos"
                files = {'source': (image.name, image.read(), image.content_type)}
                data = {'access_token': access_token}
                if message:
                    data['caption'] = message
                response = requests.post(url, data=data, files=files)
            else:
                # Text-only post: POST /{page_id}/feed
                url = f"https://graph.facebook.com/v24.0/{page_id}/feed"
                data = {'message': message, 'access_token': access_token}
                response = requests.post(url, data=data)

            if response.status_code == 200:
                messages.success(request, 'Post published successfully!')
            else:
                err_data = response.json()
                error_msg = err_data.get('error', {}).get('message', 'Unknown error')
                messages.error(request, f'Failed to publish post: {error_msg}')

        except AIAgentConfig.DoesNotExist:
            messages.error(request, 'AI Agent configuration not found.')
            return redirect('ai_agent')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')

    return redirect('feed')


@login_required
def delete_comment_view(request):
    """Delete a Facebook comment using the Graph API"""
    if request.method == 'POST':
        comment_id = request.POST.get('comment_id', '').strip()
        
        if not comment_id:
            messages.error(request, 'Please provide a valid Comment ID.')
            return redirect('report')
            
        try:
            # Get user's AI config for the access token
            ai_config = AIAgentConfig.objects.get(user=request.user)
            access_token = ai_config.facebook_page_api
            
            if not access_token:
                messages.error(request, 'Facebook Page API token is missing. Please configure your AI agent first.')
                return redirect('ai_agent')
            
            # Call Facebook Graph API
            url = f"https://graph.facebook.com/v24.0/{comment_id}?access_token={access_token}"
            response = requests.delete(url)
            
            if response.status_code == 200:
                messages.success(request, f'Comment {comment_id} deleted successfully!')
            else:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                messages.error(request, f'Failed to delete comment: {error_msg}')
                
        except AIAgentConfig.DoesNotExist:
            messages.error(request, 'AI Agent configuration not found.')
            return redirect('ai_agent')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            
    return redirect('report')


@login_required
def kyc_required_view(request):
    """Display KYC required page when user hasn't completed verification"""
    profile = getattr(request.user, 'profile', None)
    return render(request, 'accounts/kyc_required.html', {'profile': profile})


@login_required
def subscription_expired(request):
    """Display subscription expired page"""
    return render(request, 'accounts/subscription_expired.html')



def serve_protected_media(request, file_path):
    """Serve KYC documents only to admin/superuser accounts.
    Profile pictures remain publicly accessible via normal media URL.
    """
    import os
    from django.conf import settings

    # Build the full filesystem path and prevent path traversal
    full_path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, file_path))
    media_root = os.path.normpath(str(settings.MEDIA_ROOT))

    if not full_path.startswith(media_root):
        raise Http404

    if not os.path.isfile(full_path):
        raise Http404

    # Check if this is a KYC document
    if file_path.startswith('kyc_documents/'):
        # KYC docs: only admin or superuser
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if not (request.user.is_staff or request.user.is_superuser):
            raise Http404

    # For profile_pictures and any other media, serve publicly (no auth check)
    import mimetypes
    content_type, _ = mimetypes.guess_type(full_path)
    return FileResponse(open(full_path, 'rb'), content_type=content_type or 'application/octet-stream')
