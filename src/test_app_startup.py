#!/usr/bin/env python3
"""Test que la app inicia correctamente"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

if __name__ == '__main__':
    print("Verificando que la app se puede iniciar...")
    try:
        app, config = create_app()
        print("✅ App creada exitosamente")
        print("✅ Blueprints registrados:")
        transcription_rules = [rule for rule in app.url_map.iter_rules() if 'transcription' in str(rule)]
        for rule in transcription_rules[:10]:
            print(f"   - {rule}")
        if len(transcription_rules) > 10:
            print(f"   ... y {len(transcription_rules) - 10} más")
        print("\n✅ App lista para ejecutarse en puerto", config.PORT)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
