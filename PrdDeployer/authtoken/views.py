from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, reverse
from django.contrib.auth.models import User
from .models import Token


def user_token(request, user_id, token_id=123):
    user = User.objects.get(pk=user_id)
    if request.method == 'GET':
        tokens = Token.objects.filter(user=user)
        context = {
            'user': user,
            'tokens': tokens,
        }
        return render(request, 'authtoken/user_token.html', context)

    elif request.method == 'POST':
        if not request.POST.has_key('generate_key'):
            return HttpResponse("Bad request.", status=400)
        token = Token()
        token.user = user
        token.generate_key()
        token.save()
        tokens = Token.objects.filter(user=user)
        context = {
            'user': user,
            'tokens': tokens,
        }
        return render(request, 'authtoken/user_token.html', context)


def delete_token(request, user_id, token_id):
    if request.method != "POST":
        return HttpResponse("Bad request.", status=400)

    user = User.objects.get(pk=user_id)
    token = Token.objects.get(pk=token_id, user=user)
    token.delete()
    return HttpResponseRedirect(reverse('authtoken:user_token', kwargs={'user_id': user.id}))


def toggle_token(request, user_id, token_id):
    if request.method != "POST":
        return HttpResponse("Bad request.", status=400)

    user = User.objects.get(pk=user_id)
    token = Token.objects.get(pk=token_id, user=user)
    action = request.POST.get("action")
    if action == "Enable":
        token.enable()
    elif action == "Disable":
        token.disable()
    else:
        return HttpResponse("Bad request.", status=400)
    return HttpResponseRedirect(reverse('authtoken:user_token', kwargs={'user_id': user.id}))


def authtest(request):
    print Token.auth(request)
    return HttpResponse("ok")
