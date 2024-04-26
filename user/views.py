from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.generic.edit import FormView
from django.shortcuts import render
from django.urls import reverse_lazy
from .forms import SignUpForm, MinUserChangeForm


class SignUpView(FormView):
    form_class = SignUpForm
    template_name = 'registration/sign-up.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        if form.is_valid():
            # Save the user and log them in
            user = form.save()
            login(self.request, user)
        return response


@login_required(login_url='sign_up')  # automatically redirects to sign-up page if user is not authenticated
def profile(request):
    """
    shows profile of currently logged-in user
    :param request:
    :return:
    """
    user = request.user
    if request.method == 'POST':
        form = MinUserChangeForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
    else:
        form = MinUserChangeForm(instance=user)

    return render(request, 'user/profile.html', {'form': form})
