import json
import sys
from pathlib import Path
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path to allow importing backend modules
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from backend.models import db, Category, AppCategory
from backend.database import DATABASE_URL

def migrate_categories():
    """
    Migrates category and app data from app_categories.json to the database.
    - Creates 'categories' and 'app_categories' tables if they don't exist.
    - Populates them from the JSON file.
    - This script is idempotent and non-destructive for existing data.
    """
    engine = create_engine(DATABASE_URL)
    
    # Drop old tables if they exist for a clean migration
    # This is safe because we are repopulating from the JSON source of truth
    inspector = inspect(engine)
    if 'app_categories' in inspector.get_table_names():
        print("Dropping old 'app_categories' table...")
        AppCategory.__table__.drop(engine)
    if 'categories' in inspector.get_table_names():
        print("Dropping old 'categories' table...")
        Category.__table__.drop(engine)

    db.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()

    json_path = project_root / "data" / "app_categories.json"
    if not json_path.exists():
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    categories_data = data.get("categories", {})
    
    print("Starting category migration...")

    for name, details in categories_data.items():
        category = session.query(Category).filter_by(name=name).first()
        if not category:
            print(f"Creating category: {name}")
            category = Category(
                name=name,
                color=details.get("color", "#9CA3AF"),
                description=details.get("description", "")
            )
            session.add(category)
        else:
            # Update existing category details
            category.color = details.get("color", category.color)
            category.description = details.get("description", category.description)
            print(f"Category '{name}' already exists, updating details.")

        for app_name in details.get("apps", []):
            app_mapping = session.query(AppCategory).filter_by(app_name=app_name).first()
            if not app_mapping:
                print(f"  - Mapping app '{app_name}' to '{name}'")
                new_app = AppCategory(app_name=app_name, category_name=name)
                session.add(new_app)
            elif app_mapping.category_name != name:
                print(f"  - Moving app '{app_name}' from '{app_mapping.category_name}' to '{name}'")
                app_mapping.category_name = name
            else:
                print(f"  - App '{app_name}' already correctly mapped to '{name}'")

    try:
        session.commit()
        print("\nMigration successful!")
    except Exception as e:
        session.rollback()
        print(f"\nAn error occurred: {e}")
    finally:
        session.close()
        print("Session closed.")

if __name__ == "__main__":
    migrate_categories()
