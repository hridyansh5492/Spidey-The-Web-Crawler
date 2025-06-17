import sqlite3
import os

def upgrade_database(db_path="database/crawler.db"):
    """Upgrade database schema with comprehensive data extraction columns"""
    
    # Ensure database directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop existing tables to recreate with new schema
    cursor.execute('DROP TABLE IF EXISTS links')
    cursor.execute('DROP TABLE IF EXISTS pages')
    cursor.execute('DROP TABLE IF EXISTS crawl_sessions')
    cursor.execute('DROP TABLE IF EXISTS media_files')
    cursor.execute('DROP TABLE IF EXISTS seo_data')
    cursor.execute('DROP TABLE IF EXISTS content_analysis')
    cursor.execute('DROP TABLE IF EXISTS technical_data')
    
    # Enhanced crawl_sessions table
    cursor.execute('''
        CREATE TABLE crawl_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_url TEXT NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'running',
            total_pages INTEGER DEFAULT 0,
            max_pages INTEGER DEFAULT 50,
            delay REAL DEFAULT 1.0,
            domain TEXT,
            session_name TEXT,
            user_agent TEXT,
            total_media_files INTEGER DEFAULT 0,
            total_errors INTEGER DEFAULT 0,
            avg_response_time REAL DEFAULT 0.0
        )
    ''')
    
    # Enhanced pages table with comprehensive data
    cursor.execute('''
        CREATE TABLE pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            url TEXT NOT NULL,
            title TEXT,
            content TEXT,
            status_code INTEGER,
            response_time REAL,
            crawl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            word_count INTEGER,
            link_count INTEGER,
            
            -- SEO & Meta Data
            meta_description TEXT,
            meta_keywords TEXT,
            canonical_url TEXT,
            og_title TEXT,
            og_description TEXT,
            og_image TEXT,
            og_type TEXT,
            twitter_card TEXT,
            twitter_title TEXT,
            twitter_description TEXT,
            twitter_image TEXT,
            
            -- Content Analysis
            h1_tags TEXT,  -- JSON array
            h2_tags TEXT,  -- JSON array
            h3_tags TEXT,  -- JSON array
            h4_tags TEXT,  -- JSON array
            h5_tags TEXT,  -- JSON array
            h6_tags TEXT,  -- JSON array
            image_count INTEGER DEFAULT 0,
            video_count INTEGER DEFAULT 0,
            audio_count INTEGER DEFAULT 0,
            form_count INTEGER DEFAULT 0,
            email_addresses TEXT,  -- JSON array
            phone_numbers TEXT,    -- JSON array
            social_links TEXT,     -- JSON array
            
            -- Technical Data
            content_type TEXT,
            content_length INTEGER,
            server_header TEXT,
            last_modified TEXT,
            etag TEXT,
            cache_control TEXT,
            cookies_count INTEGER DEFAULT 0,
            css_files TEXT,        -- JSON array
            js_files TEXT,         -- JSON array
            
            -- Content Quality
            readability_score REAL,
            language_detected TEXT,
            keyword_density TEXT,  -- JSON object
            content_hash TEXT,
            
            FOREIGN KEY (session_id) REFERENCES crawl_sessions (id)
        )
    ''')
    
    # Enhanced links table
    cursor.execute('''
        CREATE TABLE links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER,
            url TEXT NOT NULL,
            text TEXT,
            is_internal BOOLEAN,
            link_type TEXT,  -- 'nav', 'footer', 'content', 'social'
            rel_attribute TEXT,
            target_attribute TEXT,
            title_attribute TEXT,
            FOREIGN KEY (page_id) REFERENCES pages (id)
        )
    ''')
    
    # Media files table
    cursor.execute('''
        CREATE TABLE media_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER,
            session_id INTEGER,
            url TEXT NOT NULL,
            file_type TEXT,  -- 'image', 'video', 'audio', 'document'
            file_name TEXT,
            file_size INTEGER,
            alt_text TEXT,
            title_text TEXT,
            width INTEGER,
            height INTEGER,
            format TEXT,  -- jpg, png, mp4, etc.
            local_path TEXT,  -- path to downloaded low-res version
            download_status TEXT DEFAULT 'pending',
            download_time TIMESTAMP,
            FOREIGN KEY (page_id) REFERENCES pages (id),
            FOREIGN KEY (session_id) REFERENCES crawl_sessions (id)
        )
    ''')
    
    # SEO analysis table
    cursor.execute('''
        CREATE TABLE seo_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER,
            session_id INTEGER,
            title_length INTEGER,
            meta_desc_length INTEGER,
            h1_count INTEGER,
            missing_alt_images INTEGER,
            broken_links INTEGER,
            duplicate_content BOOLEAN DEFAULT 0,
            mobile_friendly BOOLEAN DEFAULT 1,
            page_speed_score REAL,
            seo_score REAL,
            recommendations TEXT,  -- JSON array
            FOREIGN KEY (page_id) REFERENCES pages (id),
            FOREIGN KEY (session_id) REFERENCES crawl_sessions (id)
        )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX idx_pages_session_id ON pages(session_id)')
    cursor.execute('CREATE INDEX idx_pages_url ON pages(url)')
    cursor.execute('CREATE INDEX idx_links_page_id ON links(page_id)')
    cursor.execute('CREATE INDEX idx_media_session_id ON media_files(session_id)')
    cursor.execute('CREATE INDEX idx_media_page_id ON media_files(page_id)')
    
    conn.commit()
    conn.close()
    
    print("Database schema upgraded successfully!")
    print("New features added:")
    print("- Comprehensive SEO & Meta data extraction")
    print("- Content analysis (headings, images, videos, forms)")
    print("- Technical data (headers, cookies, files)")
    print("- Content quality metrics")
    print("- Media files tracking with download capability")
    print("- Enhanced session management")

if __name__ == '__main__':
    upgrade_database()