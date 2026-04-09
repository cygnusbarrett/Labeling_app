# 🎯 Aplicación de Validación de Transcripciones de Audio

Sistema colaborativo para validación manual de transcripciones automáticas de audio, con arquitectura robusta y seguridad enterprise-grade.

## 🔐 Seguridad y Configuración

### ⚠️ Configuración de Claves Secretas

**IMPORTANTE**: Este repositorio NO contiene claves secretas reales. Debes configurarlas tú mismo.

#### 1. Generar Claves Seguras

```bash
cd src/scripts
python generate_secrets.py
```

#### 2. Configurar Archivo .env

```bash
# Copiar template
cp envs/web_app.env.example envs/web_app.env

# Editar con tus claves generadas
nano envs/web_app.env
```

#### 3. Variables Requeridas

```bash
JWT_SECRET_KEY=tu_clave_jwt_segura_aqui
SECRET_KEY=tu_clave_flask_segura_aqui
DATABASE_URL=sqlite:///labeling_app.db
FLASK_ENV=development
PORT=8080
```

### 🔄 Rotación de Claves

Para rotar claves en producción:

```bash
./rotate_keys.sh
sudo systemctl restart labeling-app
```

### 📖 Documentación de Seguridad

Lee [`KEY_MANAGEMENT.md`](KEY_MANAGEMENT.md) para información completa sobre manejo de claves.

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.8+
- pip
- virtualenv

### Instalación

```bash
# Clonar repositorio
git clone <repository-url>
cd labeling_app

# Configurar entorno virtual
python -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r src/requirements/requirements.txt

# Configurar claves (ver sección de seguridad arriba)
cp envs/web_app.env.example envs/web_app.env
# Editar envs/web_app.env con tus claves

# Inicializar base de datos
cd src
python -c "from models.database import DatabaseManager; dm=DatabaseManager(); dm.create_tables(); dm.init_admin_user()"

# Ejecutar aplicación
python app.py
```

## 🏗️ Arquitectura

- **Backend**: Flask + SQLAlchemy + JWT
- **Base de Datos**: SQLite/PostgreSQL
- **Autenticación**: JWT con refresh tokens
- **Monitoreo**: Health checks + logging rotativo
- **Seguridad**: Variables de entorno + validación automática

## 📊 Características

- ✅ Validación colaborativa de transcripciones
- ✅ API REST completa
- ✅ Autenticación JWT robusta
- ✅ Monitoreo de salud integrado
- ✅ Manejo seguro de claves secretas
- ✅ Arquitectura escalable

## 🔒 Seguridad

- **Claves criptográficamente seguras**: Generadas con módulo `secrets`
- **Variables de entorno**: No hardcoded en código
- **Validación automática**: Chequeo de configuración en producción
- **Rotación periódica**: Scripts automatizados para rotación de claves
- **Auditoría**: Logs detallados de todas las operaciones

## 📚 Documentación

- [`IMPLEMENTATION_SUMMARY.md`](IMPLEMENTATION_SUMMARY.md) - Resumen técnico
- [`ROBUSTNESS_ARCHITECTURE.md`](ROBUSTNESS_ARCHITECTURE.md) - Arquitectura robusta
- [`KEY_MANAGEMENT.md`](KEY_MANAGEMENT.md) - Manejo de claves secretas
- [`DEPLOYMENT.md`](DEPLOYMENT.md) - Guía de despliegue

## 🤝 Contribución

1. **Nunca commitear claves reales**
2. **Usar variables de entorno para configuración**
3. **Seguir estándares de seguridad OWASP**
4. **Rotar claves periódicamente**

## 📄 Licencia

Ver [`LICENSE`](LICENSE)</content>
<parameter name="filePath">/Users/camilogutierrez/STEM/nuestra-memoria/Repos/Untitled/Labeling_app/README.md