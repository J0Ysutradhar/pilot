from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser, UserProfile, AIAgentConfig, PaymentRequest


class CustomUserCreationForm(UserCreationForm):
    """Form for user registration"""
    full_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
            'placeholder': 'Enter your full name'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
            'placeholder': 'Enter your email'
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
            'placeholder': 'Enter password'
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
            'placeholder': 'Confirm password'
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
            'placeholder': 'Enter your phone number'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ('email', 'password1', 'password2')


class CustomAuthenticationForm(AuthenticationForm):
    """Form for user login"""
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
            'placeholder': 'Enter your email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
            'placeholder': 'Enter password'
        })
    )


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile"""
    class Meta:
        model = UserProfile
        fields = ['name', 'profile_picture', 'mobile_number', 'home_address', 'business_info']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
                'placeholder': 'Enter your name'
            }),
            'mobile_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
                'placeholder': 'Enter your mobile number'
            }),
            'home_address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
                'placeholder': 'Enter your home address',
                'rows': 3
            }),
            'business_info': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
                'placeholder': 'Tell us about your business/Facebook page — what you sell, your services, target audience, etc.',
                'rows': 5
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
                'accept': 'image/*'
            })
        }


class KYCUploadForm(forms.ModelForm):
    """Form for KYC document upload"""
    class Meta:
        model = UserProfile
        fields = ['kyc_front_image', 'kyc_back_image']
        widgets = {
            'kyc_front_image': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
                'accept': 'image/*'
            }),
            'kyc_back_image': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
                'accept': 'image/*'
            })
        }


class AIAgentConfigForm(forms.ModelForm):
    """Form for AI agent configuration"""
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'sr-only peer',
            'id': 'ai-toggle'
        })
    )
    
    class Meta:
        model = AIAgentConfig
        fields = ['is_active', 'facebook_page_id', 'facebook_page_api', 'system_prompt', 'blocked_post_ids']
        widgets = {
            # is_active widget is defined above to override field properties
            'facebook_page_id': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
                'placeholder': 'Enter your Facebook Page ID'
            }),

            'facebook_page_api': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
                'placeholder': 'Enter your Facebook Page Api'
            }), 
                       
            'system_prompt': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200',
                'placeholder': 'Enter your AI system prompt',
                'rows': 6
            }),
            'blocked_post_ids': forms.HiddenInput()
        }


class PaymentRequestForm(forms.ModelForm):
    """Form for user to submit payment for a subscription package"""
    class Meta:
        model = PaymentRequest
        fields = ['package_name', 'payment_method', 'transaction_id']
        widgets = {
            'package_name': forms.Select(choices=[
                ('', 'Select Package'),
                ('15 Days Package', '15 Days Package (2,500 BDT)'),
                ('30 Days Package', '30 Days Package (3,000 BDT)')
            ], attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200 bg-white mb-2'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200 bg-white mb-2'
            }),
            'transaction_id': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition duration-200 mb-2',
                'placeholder': 'e.g. 9B8E7D6C5B4A'
            }),
        }
