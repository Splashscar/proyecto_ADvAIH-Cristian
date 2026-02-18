from pydoc import doc
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from firebase_admin import auth, firestore
from proyecto_advaih.Firebase_config import initialize_firebase
from functools import wraps
import requests
import os

# Create your views here.

db = initialize_firebase()

def registro_usuario(request):
    mensaje = None

    if request.method == 'POST':
        email_user = request.POST.get('email')
        password = request.POST.get('password')

        try:
            # Crear usuario en Firebase Auth
            user = auth.create_user(
                email=email_user,
                password=password
            )

            # Crear perfil en Firestore
            db.collection('perfiles').document(user.uid).set({
                'email': email_user,
                'uid': user.uid,
                'rol': 'persona_natural',
                'fecha_registro': firestore.SERVER_TIMESTAMP
            })

            mensaje = f"😊 Usuario registrado correctamente con UID: {user.uid}"

        except Exception as e:
            mensaje = f"❌ Error: {e}"

    return render(request, 'registro.html', {'mensaje': mensaje})
    


def login_required_firebase(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'uid' not in request.session:
            messages.error(request, 'Debes iniciar sesión para acceder a esta página.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view



def iniciar_sesion(request):
    if 'uid' in request.session:
        return redirect('home')  # Redirige al dashboard si ya está autenticado
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        api_key = os.getenv('FIREBASE_WEB_API_KEY')
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"

        payload = {
            'email': email,
            'password': password,
            'returnSecureToken': True
        }

        try: 
            response = requests.post(url, json=payload)
            data = response.json()

            if response.status_code == 200:
                request.session['uid'] = data['localId']
                request.session['email'] = data['email']
                request.session['idToken'] = data['idToken']

                messages.success(request, '🟢 Inicio de sesión exitoso.')
                return redirect('home')
            else:
                error_msg = data.get('error', {}).get('message', 'UNKNOWN_ERROR')

                errores_comunes = {
                    'INVALID_LOGIN_CREDENTIALS': 'La contraseña es incorrecta o el correo no es válido.',
                    'EMAIL_NOT_FOUND': 'Este correo no está registrado en el sistema.',
                    'USER_DISABLED': 'Esta cuenta ha sido inhabilitada por el administrador.',
                    'TOO_MANY_ATTEMPTS_TRY_LATER': 'Demasiados intentos fallidos. Espere unos minutos.'
                }

                mensaje_usuario = errores_comunes.get(error_msg, 'Error desconocido. Intente nuevamente.')
                messages.error(request, f"🔴 {mensaje_usuario}")

        except requests.exceptions.RequestException as e:
            messages.error(request, f"Error de conexión: {str(e)}")

    return render(request, 'login.html')


def cerrar_sesion(request):
    request.session.flush()
    messages.info(request, 'Sesión cerrada exitosamente.')
    return redirect('login')


@login_required_firebase
def home(request):
    uid = request.session.get('uid')
    datos_usuario = {}

    try:
        doc_ref = db.collection('perfiles').document(uid)
        doc = doc_ref.get()

        if doc.exists:
            datos_usuario = doc.to_dict()
        else:
            datos_usuario = {
                'email': request.session.get('email'),
                'uid': uid,
                'rol': 'desconocido',
                'fecha_registro': None
            }

    except Exception as e:
        messages.error(request, f"Error al obtener datos del usuario: {str(e)}")
    return render(request, 'home.html', {'datos_usuario': datos_usuario})

@login_required_firebase
def listar_eventos(request):
    uid = request.session.get('uid')
    eventos = []

    try:
        docs = db.collection('eventos').where('uid_usuario', '==', uid).stream()
        for doc in docs:
            evento = doc.to_dict()
            evento['id'] = doc.id
            eventos.append(evento)
    except Exception as e:
        messages.error(request, f"Error al listar eventos: {str(e)}")
    return render(request, 'eventos/listar_eventos.html', {'eventos': eventos})


@login_required_firebase
def crear_evento(request):
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')
        uid = request.session.get('uid')
        lugar = request.POST.get('lugar')
        fecha = request.POST.get('fecha')
        try:
            db.collection('eventos').add({
                'titulo': titulo,
                'descripcion': descripcion,
                'uid_usuario': uid,
                'lugar': lugar,
                'fecha': fecha,
                'fecha_creacion': firestore.SERVER_TIMESTAMP
            })
            messages.success(request, 'Evento creado exitosamente.')
            return redirect('listar_eventos')
        except Exception as e:
            messages.error(request, f"Error al crear evento: {str(e)}")
    return render(request, 'eventos/crear_evento.html')

@login_required_firebase
def eliminar_evento(request, evento_id):
    try:
        db.collection('eventos').document(evento_id).delete()
        messages.success(request, 'Evento eliminado exitosamente.')
    except Exception as e:
        messages.error(request, f"Error al eliminar evento: {str(e)}")
    return redirect('listar_eventos')

@login_required_firebase
def editar_evento(request, evento_id):
    uid = request.session.get('uid')
    evento_ref = db.collection('eventos').document(evento_id)

    try:
        doc = evento_ref.get()

        if not doc.exists:
            messages.error(request, 'Evento no encontrado.')
            return redirect('listar_eventos')
        evento_data = doc.to_dict()

        if evento_data['uid_usuario'] != uid:
            messages.error(request, 'No tienes permiso para editar este evento.')
            return redirect('listar_eventos')
        if request.method == 'POST':
            nuevo_titulo = request.POST.get('titulo')
            nueva_descripcion = request.POST.get('descripcion')
            nuevo_lugar = request.POST.get('lugar')
            nueva_fecha = request.POST.get('fecha')

            evento_ref.update({
                'titulo': nuevo_titulo,
                'descripcion': nueva_descripcion,
                'lugar': nuevo_lugar,
                'fecha': nueva_fecha,
                'fecha_actualizacion': firestore.SERVER_TIMESTAMP
            })
            messages.success(request, 'Evento actualizado exitosamente.')
            return redirect('listar_eventos')
        
        return render(request, 'eventos/editar_evento.html', {'evento': evento_data, 'evento_id': evento_id})
    except Exception as e:
        messages.error(request, f"Error al editar evento: {str(e)}")
        return redirect('listar_eventos')

