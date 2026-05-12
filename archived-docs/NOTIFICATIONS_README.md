# Sistema de Notificaciones por Telegram

Este sistema envía notificaciones automáticas al administrador cuando los usuarios completan todas sus tareas pendientes.

## Características

- 🚨 **Notificación automática**: Avisa al admin cuando un usuario no tiene más tareas
- 🛡️ **Protección anti-spam**: Limita las notificaciones a máximo 1 por hora por usuario
- 📱 **Integración con Telegram**: Usa bots de Telegram para envío de mensajes
- ⚙️ **Configurable**: Intervalos y timeouts personalizables
- 🔧 **Endpoints de administración**: Control completo desde la API

## Configuración

### 1. Crear un Bot de Telegram

1. Habla con [@BotFather](https://t.me/BotFather) en Telegram
2. Envía `/newbot` y sigue las instrucciones
3. Guarda el **token** que te proporciona (formato: `REPLACE_WITH_BOTFATHER_TOKEN`)

### 2. Obtener tu Chat ID

1. Envía un mensaje a tu bot
2. Visita: `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`
3. Busca el `chat.id` en la respuesta JSON
4. Guarda este número (puede ser positivo o negativo)

### 3. Configurar Variables de Entorno

Crea un archivo `.env` en el directorio raíz del proyecto:

```bash
# Token del bot de Telegram
TELEGRAM_BOT_TOKEN=REPLACE_WITH_BOTFATHER_TOKEN

# ID del chat del admin
TELEGRAM_ADMIN_CHAT_ID=123456789
```

### 4. Probar la Configuración

Ejecuta el script de prueba:

```bash
cd /home/cvasquez/Labeling_app
python test_notifications.py
```

## Funcionamiento

### Flujo Automático

1. **Usuario solicita tarea**: Cuando un usuario llama a `/api/v2/task/next`
2. **No hay tareas**: Si no hay tareas pendientes para el usuario
3. **Verificación anti-spam**: El sistema verifica si ya se envió una notificación reciente
4. **Envío de notificación**: Si pasa las verificaciones, se envía el mensaje al admin

### Protección Anti-Spam

- **Intervalo mínimo**: 1 hora entre notificaciones del mismo usuario
- **Estado persistente**: Recuerda qué usuarios ya fueron notificados
- **Reset automático**: Cuando se asignan nuevas tareas, se resetea el estado

### Formato del Mensaje

```
🚨 Usuario sin tareas

👤 Usuario: juan_perez (ID: 123)
📋 Estado: Ya completó todas sus tareas pendientes
⏰ Hora: 2025-08-08 14:30:00

💡 ¡Asígnale más tareas para que pueda continuar!
```

## Endpoints de Administración

### Obtener Estado de Notificaciones
```http
GET /api/v2/admin/notifications/status
```

### Resetear Estado de Usuario
```http
POST /api/v2/admin/notifications/reset/{user_id}
```

### Enviar Notificación de Prueba
```http
POST /api/v2/admin/notifications/test
Content-Type: application/json

{
  "message": "Mensaje de prueba personalizado"
}
```

### Obtener Configuración
```http
GET /api/v2/admin/notifications/config
```

## Personalización

### Modificar Intervalos

Edita el archivo `services/notification_service.py`:

```python
class NotificationService:
    def __init__(self):
        # Tiempo mínimo entre notificaciones (en segundos)
        self.min_notification_interval = 3600  # 1 hora
        
        # Tiempo para considerar notificación como reciente
        self.notification_timeout = 24 * 3600  # 24 horas
```

### Personalizar Mensajes

Edita la función `send_no_tasks_notification` en `services/notification_service.py`:

```python
message = (
    f"🚨 <b>Usuario sin tareas</b>\n\n"
    f"👤 <b>Usuario:</b> {username} (ID: {user_id})\n"
    f"📋 <b>Estado:</b> Ya completó todas sus tareas pendientes\n"
    f"⏰ <b>Hora:</b> {current_time}\n\n"
    f"💡 <i>¡Asígnale más tareas para que pueda continuar!</i>"
)
```

## Logs

El sistema registra todas las actividades:

```
INFO - Notificación de 'sin tareas' enviada exitosamente para usuario juan_perez (ID: 123)
DEBUG - Usuario juan_perez (ID: 123) ya fue notificado anteriormente
WARNING - Notificación para juan_perez bloqueada por anti-spam. Faltan 45 minutos
```

## Solución de Problemas

### Bot no envía mensajes
- Verifica que el token sea correcto
- Asegúrate de que el bot esté activo
- Comprueba que el chat ID sea correcto

### Notificaciones no se envían
- Revisa los logs de la aplicación
- Ejecuta `test_notifications.py` para diagnosticar
- Verifica la conectividad a internet

### Spam de notificaciones
- El sistema incluye protección automática
- Usa `/api/v2/admin/notifications/status` para verificar estado
- Resetea usuarios específicos si es necesario

## Seguridad

- ✅ Rate limiting en endpoints sensibles
- ✅ Validación de entrada en todas las rutas
- ✅ Protección anti-spam integrada
- ✅ Solo admins pueden gestionar notificaciones
- ✅ Logs detallados para auditoría
