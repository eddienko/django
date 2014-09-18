
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render

class UserCreationFormCasu(UserCreationForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "username")

def register(request):
    if request.method == 'POST':
        form = UserCreationFormCasu(request.POST)
        if form.is_valid():
            new_user = form.save()
            return HttpResponseRedirect("/accounts/login/")
    else:
        form = UserCreationFormCasu()
    return render(request, "registration/register.html", {
        'form': form,
    })