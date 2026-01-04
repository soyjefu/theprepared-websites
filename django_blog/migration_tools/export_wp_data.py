import mysql.connector
import json
import os
import datetime

# Database Configuration
DB_CONFIG = {
    'user': 'theprepared',
    'password': 'dnflxksdir1!',
    'host': 'mariadb_db',
    'database': 'php_db',
}

OUTPUT_DIR = '/app/migration_tools/data'

def datetime_converter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()

def export_data():
    conn = None
    try:
        print(f"Connecting to {DB_CONFIG['host']}...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # 1. Export Posts
        print("Exporting Posts...")
        # Fetching posts of type 'post' and 'page' (optional, sticking to 'post' for now per plan)
        # Also fetching attachment for media handling if needed, but 'post' is main priority.
        query_posts = "SELECT * FROM wp_posts WHERE post_type = 'post' AND post_status IN ('publish', 'draft')"
        cursor.execute(query_posts)
        posts = cursor.fetchall()
        
        with open(os.path.join(OUTPUT_DIR, 'posts.json'), 'w', encoding='utf-8') as f:
            json.dump(posts, f, default=datetime_converter, ensure_ascii=False, indent=4)
        print(f"Exported {len(posts)} posts.")

        # 2. Export Terms (Categories and Tags)
        print("Exporting Terms...")
        query_terms = """
            SELECT t.term_id, t.name, t.slug, tt.taxonomy, tt.term_taxonomy_id 
            FROM wp_terms t 
            JOIN wp_term_taxonomy tt ON t.term_id = tt.term_id 
            WHERE tt.taxonomy IN ('category', 'post_tag')
        """
        cursor.execute(query_terms)
        terms = cursor.fetchall()

        with open(os.path.join(OUTPUT_DIR, 'terms.json'), 'w', encoding='utf-8') as f:
            json.dump(terms, f, default=datetime_converter, ensure_ascii=False, indent=4)
        print(f"Exported {len(terms)} terms.")

        # 3. Export Relationships
        print("Exporting Relationships...")
        query_rels = "SELECT object_id, term_taxonomy_id FROM wp_term_relationships"
        cursor.execute(query_rels)
        relationships = cursor.fetchall()

        with open(os.path.join(OUTPUT_DIR, 'relationships.json'), 'w', encoding='utf-8') as f:
            json.dump(relationships, f, default=datetime_converter, ensure_ascii=False, indent=4)
        print(f"Exported {len(relationships)} relationships.")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if conn and conn.is_connected():
            conn.close()
            print("Connection closed.")

if __name__ == "__main__":
    # Ensure output directory exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    export_data()
