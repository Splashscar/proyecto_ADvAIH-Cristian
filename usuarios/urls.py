from django.urls import path
from .views import registro_usuario, home, cerrar_sesion
from . import views
urlpatterns = [
    #asociar la funcion a la vista con url /registro/
    path('registro/', views.registro_usuario, name = 'registro'),
    
    #Ruta para el inicio de sesion
    path('login/', views.iniciar_sesion, name='login'),
    path('home/', views.home, name='home'),
    path('logout/', views.cerrar_sesion, name='logout'),
    path('eventos/', views.listar_eventos, name='listar_eventos'),
    path('eventos/crear/', views.crear_evento, name='crear_evento'),
    path('eventos/editar/<str:evento_id>/', views.editar_evento, name='editar_evento'),
    path('eventos/eliminar/<str:evento_id>/', views.eliminar_evento, name='eliminar_evento'),

]

