import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import sqlite3
import json
from datetime import datetime
import re
from collections import deque
import threading
import os
import hashlib
from langdetect import detect
from textstat import flesch_reading_ease

class WebCrawler:
    def __init__(self, db_path="database/crawler.db"):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs("exports", exist_ok=True)
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crawl_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_url TEXT NOT NULL,
                max_pages INTEGER,
                delay REAL,
                domain TEXT,
                session_name TEXT,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                status TEXT DEFAULT 'running',
                total_pages INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                url TEXT NOT NULL,
                title TEXT,
                content TEXT,
                status_code INTEGER,
                response_time REAL,
                word_count INTEGER,
                language_detected TEXT,
                readability_score REAL,
                content_hash TEXT,
                crawl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES crawl_sessions (id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id INTEGER,
                session_id INTEGER,
                url TEXT NOT NULL,
                text TEXT,
                is_internal BOOLEAN,
                link_type TEXT,
                FOREIGN KEY (page_id) REFERENCES pages (id),
                FOREIGN KEY (session_id) REFERENCES crawl_sessions (id)
            )
        """)
        conn.commit()
        conn.close()

    def start_crawl(self, start_url, max_pages=20, delay=3.0):
        max_pages = min(max_pages, 50)
        delay = min(delay, 5.0)
        domain = urlparse(start_url).netloc
        session_name = f"{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO crawl_sessions (start_url, max_pages, delay, domain, session_name)
            VALUES (?, ?, ?, ?, ?)
        """, (start_url, max_pages, delay, domain, session_name))
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()

        thread = threading.Thread(target=self._crawl_worker, args=(session_id, start_url, max_pages, delay))
        thread.daemon = True
        thread.start()
        return {'success': True, 'session_id': session_id, 'session_name': session_name}

    def _crawl_worker(self, session_id, start_url, max_pages, delay):
        visited = set()
        to_visit = deque([start_url])
        pages_crawled = 0
        content_hashes = set()
        base_domain = urlparse(start_url).netloc

        while to_visit and pages_crawled < max_pages:
            current_url = to_visit.popleft()
            if current_url in visited:
                continue
            visited.add(current_url)

            print(f"Crawling: {current_url}")
            page_data = self._crawl_page(session_id, current_url, content_hashes)

            if page_data:
                pages_crawled += 1
                links = self._extract_links(page_data['soup'], current_url, base_domain)
                self._save_links(session_id, page_data['page_id'], links)

                for link in links:
                    if link['is_internal'] and link['url'] not in visited and link['url'] not in to_visit:
                        to_visit.append(link['url'])

            self._update_session_progress(session_id, pages_crawled)
            print(f"Pages Crawled: {pages_crawled}/{max_pages} | Queue: {len(to_visit)}")
            time.sleep(delay)

        self._complete_session(session_id, pages_crawled)
        print(f"Session complete: {pages_crawled} pages crawled.")

    def _crawl_page(self, session_id, url, content_hashes):
        try:
            start = time.time()
            response = self.session.get(url, timeout=10)
            response_time = time.time() - start
            if response.status_code != 200:
                return None
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string.strip() if soup.title else 'No Title'
            content = self._extract_clean_content(soup)
            content_hash = hashlib.md5(content.encode()).hexdigest()
            if content_hash in content_hashes:
                return None
            content_hashes.add(content_hash)

            word_count = len(content.split())
            try:
                language = detect(content) if len(content) > 50 else 'unknown'
            except:
                language = 'unknown'
            try:
                readability = flesch_reading_ease(content)
            except:
                readability = 0

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pages (session_id, url, title, content, status_code, response_time,
                                   word_count, language_detected, readability_score, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, url, title, content, response.status_code, response_time,
                  word_count, language, readability, content_hash))
            page_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return {'page_id': page_id, 'soup': soup}
        except Exception as e:
            print(f"Failed to crawl {url}: {e}")
            return None

    def _extract_clean_content(self, soup):
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return re.sub(r'\s+', ' ', soup.get_text()).strip()

    def _extract_links(self, soup, base_url, domain):
        links = []
        for tag in soup.find_all('a', href=True):
            href = urljoin(base_url, tag['href'])  # Normalize relative links
            parsed = urlparse(href)

            # Only allow http(s) links
            if parsed.scheme not in ['http', 'https']:
                continue

            # Determine if link is internal
            netloc = parsed.netloc
            is_internal = (netloc == '' or netloc == domain)

            links.append({
                'url': href,
                'text': tag.get_text(strip=True)[:200],
                'is_internal': is_internal,
                'link_type': 'internal' if is_internal else 'external'
            })

        return links

    def _save_links(self, session_id, page_id, links):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for link in links:
            cursor.execute("""
                INSERT INTO links (page_id, session_id, url, text, is_internal, link_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (page_id, session_id, link['url'], link['text'], link['is_internal'], link['link_type']))
        conn.commit()
        conn.close()

    def _update_session_progress(self, session_id, pages_crawled):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE crawl_sessions SET total_pages = ? WHERE id = ?", (pages_crawled, session_id))
        conn.commit()
        conn.close()

    def _complete_session(self, session_id, total_pages):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE crawl_sessions SET end_time = CURRENT_TIMESTAMP, status = 'completed', total_pages = ?
            WHERE id = ?
        """, (total_pages, session_id))
        conn.commit()
        conn.close()

    def get_sessions(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM crawl_sessions ORDER BY start_time DESC")
        columns = [desc[0] for desc in cursor.description]
        result = cursor.fetchall()
        conn.close()
        return [dict(zip(columns, row)) for row in result]

    def get_session_pages(self, session_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pages WHERE session_id = ?", (session_id,))
        columns = [desc[0] for desc in cursor.description]
        result = cursor.fetchall()
        conn.close()
        return [dict(zip(columns, row)) for row in result]

    def export_session_data(self, session_id, format_type='json'):
        session = next((s for s in self.get_sessions() if s['id'] == session_id), None)
        if not session:
            return None
        pages = self.get_session_pages(session_id)
        export_data = {
            'session': session,
            'pages': pages,
            'export_time': datetime.now().isoformat()
        }
        if format_type == 'json':
            export_path = f"exports/session_{session_id}_export.json"
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2)
            return export_path
        return None
