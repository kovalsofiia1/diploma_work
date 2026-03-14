import json
import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal, create_all_tables
from app.models.event import City

def seed_cities():
    create_all_tables()
    db = SessionLocal()
    try:
        # Load karabas cities
        karabas_path = os.path.join(os.path.dirname(__file__), "..", "site-parsers", "karabas", "karabas-cities.json")
        concert_ua_path = os.path.join(os.path.dirname(__file__), "..", "site-parsers", "concert-ua", "concert-ua-cities.json")
        
        cities_set = set()
        cities_set.add("Online")
        
        if os.path.exists(karabas_path):
            with open(karabas_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if "name" in item:
                        cities_set.add(item["name"].strip())
                        
        if os.path.exists(concert_ua_path):
            with open(concert_ua_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if "name" in item:
                        cities_set.add(item["name"].strip())
                        
        # Get existing cities
        existing_cities = {c.name for c in db.query(City).all()}
        
        # Add new cities
        new_cities = cities_set - existing_cities
        if new_cities:
            for city_name in new_cities:
                db.add(City(name=city_name))
            db.commit()
            print(f"Added {len(new_cities)} new cities.")
        else:
            print("No new cities to add.")
            
    except Exception as e:
        print(f"Error seeding cities: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_cities()
