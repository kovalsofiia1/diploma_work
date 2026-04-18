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
        
        cities_map = {"Online": None}
        
        if os.path.exists(karabas_path):
            with open(karabas_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if "name" in item:
                        name = item["name"].strip()
                        if not name:
                            continue
                        subdomain = (item.get("subdomain") or "").strip() or None
                        if name not in cities_map or (subdomain and not cities_map[name]):
                            cities_map[name] = subdomain
                        
        if os.path.exists(concert_ua_path):
            with open(concert_ua_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if "name" in item:
                        name = item["name"].strip()
                        if not name:
                            continue
                        slug = (item.get("slug") or "").strip() or None
                        if name not in cities_map or (slug and not cities_map[name]):
                            cities_map[name] = slug
                        
        # Get existing cities
        existing_cities = {c.name for c in db.query(City).all()}
        
        # Add new cities
        new_cities = set(cities_map.keys()) - existing_cities
        if new_cities:
            for city_name in new_cities:
                db.add(City(name=city_name, name_en=cities_map.get(city_name)))
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
