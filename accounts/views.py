from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from .forms import UserUpdateForm, UserRegisterForm
from django.contrib import messages



def register(request):
    if request.user.is_authenticated:
        return redirect('/')
    
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to Twi Bridge, {user.username}!')
            return redirect('/')
    else:
        form = UserRegisterForm()
    
    return render(request, 'accounts/register.html', {'form': form})
    
@login_required
def profile_view(request):
    if request.method == 'POST':
        # Check which form was submitted
        if 'update_profile' in request.POST:
            u_form = UserUpdateForm(request.POST, instance=request.user)
            p_form = PasswordChangeForm(request.user)
            if u_form.is_valid():
                u_form.save()
                messages.success(request, 'Your profile has been updated!')
                return redirect('profile')
        elif 'change_password' in request.POST:
            p_form = PasswordChangeForm(request.user, request.POST)
            u_form = UserUpdateForm(instance=request.user)
            if p_form.is_valid():
                user = p_form.save()
                update_session_auth_hash(request, user) # Important! Keep user logged in
                messages.success(request, 'Your password was successfully updated!')
                return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = PasswordChangeForm(request.user)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'accounts/profile.html', context)

class UserLoginView(SuccessMessageMixin, LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    success_message = "Welcome back, %(username)s!"

    def get_success_message(self, cleaned_data):
        return self.success_message % dict(
            cleaned_data,
            username=self.request.user.username,
        )
