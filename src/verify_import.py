#!/usr/bin/env python3
"""
Verificar que los datos fueron importados correctamente
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from models.database import DatabaseManager, Segment, Word

db_manager = DatabaseManager()
session = db_manager.get_session()

try:
    # Verificar segmentos
    segment_count = session.query(Segment).count()
    word_count = session.query(Word).count()
    pending_segments = session.query(Segment).filter_by(review_status='pending').count()
    approved_segments = session.query(Segment).filter_by(review_status='approved').count()
    
    print("\n" + "="*60)
    print("📊 ESTADO DE LA BASE DE DATOS")
    print("="*60)
    print(f"📋 Segmentos totales:        {segment_count}")
    print(f"📝 Palabras totales:         {word_count}")
    print(f"🔴 Segmentos pendientes:    {pending_segments}")
    print(f"🟢 Segmentos aprobados:     {approved_segments}")
    print("="*60 + "\n")
    
    # Mostrar ejemplo de segmento con palabras
    segment = session.query(Segment).first()
    if segment:
        print(f"📌 Ejemplo de segmento (ID={segment.id}):")
        print(f"   Texto: {segment.text[:100]}...")
        print(f"   Estado: {segment.review_status}")
        print(f"   Palabras: {len(segment.words)}")
        if segment.words:
            word = segment.words[0]
            print(f"\n   👉 Primera palabra:")
            print(f"      Palabra: '{word.word}'")
            print(f"      Probabilidad: {word.probability:.2%}")
            print(f"      Tiempo: {word.start_time:.2f}s - {word.end_time:.2f}s")
    
finally:
    session.close()

print("✅ Base de datos verificada exitosamente\n")
