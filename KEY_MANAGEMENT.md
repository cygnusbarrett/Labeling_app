# 🔐 MANEJO DE CLAVES SECRETAS

## 📋 Resumen Ejecutivo

Este proyecto implementa un sistema robusto de manejo de claves secretas siguiendo las mejores prácticas de la industria de seguridad.

## 🏗️ Arquitectura de Seguridad

### Método de Manipulación de Claves

1. **Variables de Entorno**: Todas las claves se configuran vía variables de entorno
2. **Archivo .env**: Configuración local en `envs/web_app.env` (NO commiteado)
3. **Validación Automática**: Chequeo de fortaleza en producción
4. **Generación Segura**: Uso del módulo `secrets` de Python

### Claves Gestionadas

| Clave | Propósito | Requisitos | Rotación |
|-------|-----------|------------|----------|
| `JWT_SECRET_KEY` | Firma de tokens JWT | ≥32 caracteres | Mensual |
| `SECRET_KEY` | Sesiones Flask | ≥32 caracteres | Mensual |
| `DATABASE_URL` | Conexión BD | Válida | Según cambios |
| `TELEGRAM_*` | Notificaciones | Válidos | Según necesidad |

## 🚀 Proceso de Configuración

### 1. Generación de Claves Seguras

```bash
# Ejecutar script de generación
cd src/scripts
python generate_secrets.py

# O generar manualmente
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))"
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
```

### 2. Configuración del Archivo .env

```bash
# Copiar template
cp envs/web_app.env.example envs/web_app.env

# Editar con claves generadas
nano envs/web_app.env
```

### 3. Validación

```bash
# Verificar configuración
cd src
python -c "from config import Config; c=Config.from_env(); c.validate_production_config()"
```

## 🔄 Rotación de Claves

### Proceso de Rotación

1. **Generar nuevas claves**
2. **Actualizar archivo .env**
3. **Reiniciar aplicación**
4. **Invalidar tokens existentes** (si es JWT_SECRET_KEY)
5. **Monitorear logs por errores**

### Comando de Rotación

```bash
#!/bin/bash
# rotate_keys.sh

# Generar nuevas claves
NEW_JWT=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Backup del archivo actual
cp envs/web_app.env envs/web_app.env.backup

# Actualizar
sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$NEW_JWT/" envs/web_app.env
sed -i "s/SECRET_KEY=.*/SECRET_KEY=$NEW_SECRET/" envs/web_app.env

# Reiniciar aplicación
sudo systemctl restart labeling-app

echo "✅ Claves rotadas exitosamente"
```

## 🛡️ Medidas de Seguridad

### Protección del Repositorio

- **.gitignore configurado**: Archivos `.env` excluidos
- **Validación pre-commit**: Chequeo de claves hardcoded
- **Auditoría**: Logs de cambios en configuración

### Validaciones en Código

```python
# config.py - Validación automática
def validate_production_config(self):
    if not self.JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY es obligatorio en producción")
    elif len(self.JWT_SECRET_KEY) < 32:
        raise ValueError("JWT_SECRET_KEY debe tener al menos 32 caracteres")
```

### Generación Criptográficamente Segura

```python
import secrets

# JWT Key (86 caracteres, URL-safe base64)
jwt_key = secrets.token_urlsafe(64)

# Flask Key (64 caracteres hexadecimal)
flask_key = secrets.token_hex(32)
```

## 📊 Conformidad con Estándares

### OWASP Top 10
- ✅ **A02:2021 - Cryptographic Failures**: Mitigado con claves seguras
- ✅ **A05:2021 - Security Misconfiguration**: Validación automática

### NIST SP 800-63B
- ✅ **Longitud de claves**: ≥32 caracteres
- ✅ **Generación segura**: Módulo `secrets`
- ✅ **Rotación periódica**: Recomendada mensual

### ISO 27001
- ✅ **Control A.9.2.1**: Políticas de acceso
- ✅ **Control A.12.4.3**: Gestión de claves

## 🚨 Alertas de Seguridad

### Detección de Problemas

El sistema incluye alertas automáticas para:

- Claves débiles (<32 caracteres)
- Claves faltantes en producción
- Archivos .env en repositorio
- Uso de claves por defecto

### Respuesta a Incidentes

1. **Inmediata**: Rotar todas las claves
2. **Análisis**: Revisar logs de acceso
3. **Notificación**: Alertar a usuarios afectados
4. **Monitoreo**: Aumentar vigilancia

## 📚 Referencias

- [OWASP Secret Management](https://owasp.org/www-project-cheat-sheets/cheatsheets/Secrets_Management_Cheat_Sheet)
- [NIST SP 800-63B](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [Python secrets module](https://docs.python.org/3/library/secrets.html)</content>
<parameter name="filePath">/Users/camilogutierrez/STEM/nuestra-memoria/Repos/Untitled/Labeling_app/KEY_MANAGEMENT.md