#!/usr/bin/env python
import sys
sys.path.insert(0, '/Users/camilogutierrez/STEM/nuestra-memoria/Repos/Untitled/Labeling_app/src')

from models.database import DatabaseManager, Word, TranscriptionProject
from config import Config

config = Config.from_env()
db = DatabaseManager(config.DATABASE_URL)
session = db.get_session()

total_words = session.query(Word).count()
total_projects = session.query(TranscriptionProject).count()

print(f"✅ Total palabras: {total_words}")
print(f"✅ Total proyectos: {total_projects}")

if total_projects > 0:
    for p in session.query(TranscriptionProject).all():
        word_count = session.query(Word).filter_by(project_id=p.id).count()
        print(f"  - Proyecto: {p.name} ({word_count} palabras)")

session.close()
