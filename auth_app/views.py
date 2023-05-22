from django.shortcuts import render, redirect
from django.core.handlers.wsgi import WSGIRequest
from django.contrib import auth
from django.contrib.auth.models import User
from auth_app.service.validator.validators import RegisterValidator, EditValidator
from auth_app.service.validator.exceptions.expection import ValidateException
from auth_app.service.validator import ERROR_MESSAGE
import json


def login(request: WSGIRequest):
    login_values = request.POST.get('login_values')
    if login_values:
        login_values = json.loads(login_values.replace("'", "\""))
    if request.method == 'POST' and not login_values:
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_page = request.GET.get('next_page')
        user: User = auth.authenticate(request, username=username, password=password)
        if user is None:
            return render(request, 'login.html', {
                'error': 'Неверный логин или пароль',
            })
        if user.is_active:
            auth.login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home_page')
        if next_page is not None:
            return redirect(next_page)
    return render(request, 'login.html', {'login_values': login_values})


def register(request: WSGIRequest):
    register_params = request.POST.get('error_params')
    if register_params:
        register_params = json.loads(register_params.replace("'", "\""))
    if request.method == 'POST' and not register_params:
        request_data = request.POST.dict()
        try:
            RegisterValidator(request_data).validate()
        except ValidateException as exception:
            return render(request, 'errors.html', {
                'errors': exception.errors_list,
                'params': exception.params,
            })
        except BaseException:
            return render(request, 'errors.html', {'errors': ERROR_MESSAGE.UNKNOWN_ERROR})
        username = request_data['username']
        password = request_data['password']
        new_user = User()
        new_user.username = username
        new_user.set_password(password)
        new_user.email = request_data['email']
        new_user.name = request_data['name']
        new_user.phone = request_data['phone']
        try:
            new_user.save()
        except Exception as e:
            return render(request, 'errors.html', {
                'errors': [f'{ERROR_MESSAGE.USER_CREATE_FAIL.format(username)}', f'Ошибка сервера: {e}']
            })
        return render(request, 'info.html', {
            'message': f'Пользователь {username} успешно зарегистрирован в системе!',
            'login_values': {'username': username, 'password': password}
        })
    return render(request, 'register.html', {
        'register_params': register_params,
    })


def logout(request: WSGIRequest):
    auth.logout(request)
    return redirect('login')


def edit(request: WSGIRequest):
    if request.method == 'POST':
        request_data = request.POST.dict()
        db_username = request.user.username
        try:
            EditValidator(request_data, db_username).validate()
        except ValidateException as exception:
            return render(request, 'edit.html', {
                'errors': exception.errors_list,
                'params': exception.params,
            })
        except BaseException:
            return render(request, 'edit.html', {'errors': [ERROR_MESSAGE.UNKNOWN_ERROR]})

        user: User = User.objects.filter(username=db_username).first()
        user.username = request_data['username']
        user.email = request_data['email']
        user.first_name = request_data['first_name']
        user.last_name = request_data['last_name']
        # user.phone = request_data['phone']
        try:
            user.save()
        except Exception as e:
            return render(request, 'errors.html', {
                'errors': [f'{ERROR_MESSAGE.USER_EDIT_FAIL.format(user.username)}', f'Ошибка сервера: {e}']
            })
        return render(request, 'info.html', {
            'message': f'Данные о {user.username} успешно изменены в системе!',
        })
    return render(request, 'edit.html')


def user_list(request: WSGIRequest):
    if request.user.is_superuser:
        users = User.objects.all()
        return render(request, 'user_list.html', {
            'users': users.order_by('id')
        })
    return render(request, 'info.html', {
        'message': 'У вас недостаточно прав на просмотр этой страницы.'
    })


def filter_users(request: WSGIRequest):
    if request.user.is_superuser:
        query = request.POST.get('filter')
        users = User.objects.filter(username__icontains=query).all()
        return render(request, 'user_list.html', {
            'users': users
        })
    return render(request, 'info.html', {
        'message': 'У вас недостаточно прав на просмотр этой страницы.'
    })


def quick_login(request: WSGIRequest):
    user_id = request.POST.get('user_id')
    user = User.objects.get(pk=user_id)
    auth.login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('home_page')


def ask(request: WSGIRequest):
    user_id = request.POST.get('delete_id')
    user = User.objects.get(pk=user_id)
    return render(request, 'info.html', {
        'message': f'Удалить пользователя {user.username}?',
        'delete_id': user_id
    })


def delete(request: WSGIRequest):
    user_id = request.POST.get('delete_id')
    user = User.objects.get(pk=user_id)
    if user.is_superuser:
        return render(request, 'info.html', {
            'message': f'Администраторов удалять нельзя. {user.username}',
        })
    if user:
        user.is_active = False
        user.save()
    return redirect('user_list')
