from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import ContactForm
from .models import contact,Login
from django.contrib.auth.models import User , auth
from .mail import send_email
from .whatsapp import send_whatsapp
from .location import lat, log, location, city, state
from .forms import UserCreateForm , LoginForm
from django.core.mail import EmailMessage
from django.views import View
from django.utils.encoding import force_bytes , force_text , DjangoUnicodeDecodeError
from django.utils.http  import urlsafe_base64_encode , urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from .utils import account_activation_token
from django.http import HttpResponse

# Create your views here

def home(request):
    context = {}    
    return render(request, 'main_app/home.html', context)

def register(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            email=form.cleaned_data.get('email')
            user.is_active=False
            user.save()

            uidb64=urlsafe_base64_encode(force_bytes(user.pk))
            domain=get_current_site(request).domain
            link=reverse('activate',kwargs={'uidb64':uidb64,'token':account_activation_token.make_token(user)})
            
            activate_url = 'http://'+domain+link

            email_subject="Rescue - Activate you Account!"
            email_body= "Hi  "+user.username+"  ,  Please use this link to verify your account\n" + activate_url
            email = EmailMessage(
                email_subject,
                email_body,
                'noreply@gmail.com',
                [email],
            )
            messages.success(request, f"New Account Created Successfully: {username}")
            messages.success(request, f"Check your email to Activate your account!")
            email.send(fail_silently=False)
            return redirect('main_app:home')
        else:
            for msg in form.error_messages:
                messages.error(request, f"{msg}: form.error_messages[msg]")
        
    else:
        form = UserCreateForm()
    return render(request, 'main_app/register.html', {'form': form})

class VerificationView(View):
    def get(self, request, uidb64, token):
        try:
            id = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=id)

            if not account_activation_token.check_token(user, token):
                return redirect('main_app:login'+'?message='+'User already activated')

            if user.is_active:
                return redirect('main_app:login')
            user.is_active = True
            user.save()

            messages.success(request, f'Account activated successfully')
            return redirect('main_app:login')

        except Exception as ex:
            pass

        return redirect('main_app:login')
 

def logout_request(request):
    logout(request)
    messages.info(request, "Logged out successfully!")
    return redirect("main_app:home")


def login_request(request):
    form = LoginForm(request.POST)
    username = request.POST.get('Username_or_Email')
    password = request.POST.get('password')
    if request.method == "POST":  
        if username and password:          
            if(User.objects.filter(username=username).exists()):
                user=auth.authenticate(username=username,password=password)
                if user:
                    if user.is_active:
                        login(request, user)
                        messages.success(request, 'Welcome, ' +
                                        user.username+' you are now logged in')
                        return redirect('main_app:home')
                    
                messages.error(request, "Account is not active,please check your email")
                    

            elif(User.objects.filter(email=username).exists()):
                user=User.objects.get(email=username)
                user=auth.authenticate(username=user.username,password=password)
                if user:
                    if user.is_active:
                        login(request, user)
                        messages.success(request, 'Welcome, ' +
                                        user.username+' you are now logged in')
                        return redirect('main_app:home')
                    
                messages.error(request, "Account is not active,please check your email")
                    
            else:
                messages.error(request, f"Invalid username or password")
                return redirect("main_app:login")
        
            
    form = LoginForm()
    return render(request, "main_app/login.html", {'form': form})


def emergency_contact(request):
    users = User.objects.all()
    curr = 0
    for user in users:
        if request.user.is_authenticated:
            curr = user
            break
    if curr==0:
        return redirect("main_app:login")
    contacts = contact.objects.filter(user=request.user)
    total_contacts = contacts.count()
    context = {'contacts': contacts, 'total_contacts': total_contacts, 'user':request.user}
    return render(request, 'main_app/emergency_contact.html', context)


def create_contact(request):
    inst = contact(user=request.user)
    form = ContactForm(instance=inst)
    if request.method == 'POST':
        form = ContactForm(request.POST, instance=inst)
        if form.is_valid():
            form.save()
            messages.info(request, f"New contact created successfully!!")
            messages.info(request, f"An email has been sent to your contact!!")
            return redirect('main_app:emergency_contact')
        messages.error(request, f"Invalid username or password")
    context = {'form': form}
    return render(request, 'main_app/create_contact.html', context)


def update_contact(request, pk):
    curr_contact = contact.objects.get(id=pk)
    name = curr_contact.name
    form = ContactForm(initial={'name':name,'email':curr_contact.email,'mobile_no':curr_contact.mobile_no,'relation':curr_contact.relation})
    if request.method == 'POST':
        form = ContactForm(request.POST, instance=curr_contact)
        if form.is_valid():
            form.save()
            messages.error(request, f"{name} updated successfully!!")
            messages.info(request, f"A message has been sent to your contact!!")
            return redirect('main_app:emergency_contact')
    context = {'form': form}
    return render(request, 'main_app/create_contact.html', context)


def delete_contact(request, pk):
    curr_contact = contact.objects.get(id=pk)
    name = curr_contact.name
    if request.method == "POST":
        curr_contact.delete()
        messages.error(request, f"{name} deleted successfully!!")
        return redirect('main_app:emergency_contact')
    context = {'item': curr_contact}
    return render(request, 'main_app/delete_contact.html', context)


def emergency(request):
    users = User.objects.all()
    curr = 0
    for user in users:
        if request.user.is_authenticated:
            curr = user
            break
    if curr == 0:
        return redirect("main_app:login")
    contacts = contact.objects.filter(user=request.user)
    total_contacts = contacts.count()
    context = {'contacts': contacts, 'total_contacts': total_contacts, 'user':request.user}
    emails, mobile_numbers = [], []
    for j in contacts:
        emails.append(j._meta.get_field("email"))
        mobile_numbers.append(str(j.mobile_no).replace(" ", ""))
    name = request.user.username
    link = "http://www.google.com/maps/place/"+lat+","+log
    for c in contacts:
        send_email(name, c.email, link)
    try:
        send_whatsapp(mobile_numbers, name, link)
    except:
        messages.error(request, "your contact numbers contains number without country code.")
    return render(request,'main_app/emergency_contact.html',context)


def helpline_numbers(request):
    return render(request, 'main_app/helpline_numbers.html', {'title': 'helpline_numbers'})


def ngo_details(request):
    return render(request, 'main_app/ngo_details.html', {'title': 'ngo_details'})


def women_laws(request):
    return render(request, 'main_app/women_laws.html', {'title': 'women_laws'})


def developers(request):
    return render(request, 'main_app/developers.html', {'title': 'developers'})


def women_rights(request):
    return render(request, 'main_app/women_rights.html', {'title': 'women_rights'})

def page_not_found(request):
    return render(request, 'main_app/404.html', {'title': '404_error'})