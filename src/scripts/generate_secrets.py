#!/usr/bin/env python3
"""
Script para generar claves secretas seguras para la aplicación

Uso:
    cd src/scripts
    python generate_secrets.py
"""
import secrets
import sys

def generate_jwt_secret():
    """Genera una clave JWT segura (86 caracteres URL-safe)"""
    return secrets.token_urlsafe(64)

def generate_flask_secret():
    """Genera una clave Flask segura (64 caracteres hexadecimales)"""
    return secrets.token_hex(32)

def main():
    print("=" * 70)
    print("🔐 GENERADOR DE CLAVES SECRETAS PARA LA APLICACIÓN")
    print("=" * 70)
    
    jwt_secret = generate_jwt_secret()
    flask_secret = generate_flask_secret()
    
    print("\n✅ Claves generadas exitosamente:")
    print(f"\nJWT_SECRET_KEY={jwt_secret}")
    print(f"SECRET_KEY={flask_secret}")
    
    print("\n" + "=" * 70)
    print("📝 INFORMACIÓN DE CLAVES")
    print("=" * 70)
    print(f"JWT_SECRET_KEY: {len(jwt_secret)} caracteres")
    print(f"SECRET_KEY: {len(flask_secret)} caracteres")
    
    print("\n" + "=" * 70)
    print("⚠️  INSTRUCCIONES IMPORTANTES")
    print("=" * 70)
    print("1. Copia estas claves a tu archivo envs/web_app.env")
    print("2. NUNCA compartas estas claves públicamente")
    print("3. Usa diferentes claves para desarrollo y producción")
    print("4. Rota las claves periódicamente en producción")
    print("5. Usa 'bash rotate_keys.sh' para automatizar la rotación")
    
    print("\n" + "=" * 70)
    print("📄 EJEMPLO DE ARCHIVO .env")
    print("=" * 70)
    with open("example_env.txt", "w") as f:
        f.write("# Configuracion de la Aplicacion Web\n")
        f.write(f"JWT_SECRET_KEY={jwt_secret}\n")
        f.write(f"SECRET_KEY={flask_secret}\n")
        f.write("DATABASE_URL=sqlite:///labeling_app.db\n")
        f.write("FLASK_ENV=development\n")
        f.write("PORT=8080\n")
    
    print("# Configuracion de la Aplicacion Web")
    print(f"JWT_SECRET_KEY={jwt_secret}")
    print(f"SECRET_KEY={flask_secret}")
    print("DATABASE_URL=sqlite:///labeling_app.db")
    print("FLASK_ENV=development")
    print("PORT=8080")
    
    print("\n✅ Archivo de ejemplo guardado como 'example_env.txt'")
    return 0

if __name__ == '__main__':
    sys.exit(main())
