from django.shortcuts import render

def users(request):
    return render(request, 'users/profile.html')

def login(request):
    return render(request, 'users/login.html')

def register(request):
    return render(request, 'users/register.html')

def profile(request):
    return render(request, 'users/profile.html')
def logout(request):
    return render(request, 'users/logout.html')
def user_loans(request):
    return render(request, 'users/user_loans.html')
