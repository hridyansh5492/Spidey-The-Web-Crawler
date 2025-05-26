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

class WebCrawler:
    def __init__(self, db_path="database/crawler.db"):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.setup_database()
        
    def setup_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create crawl_sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crawl_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_url TEXT NOT NULL,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                status TEXT DEFAULT 'running',
                total_pages INTEGER DEFAULT 0,
                max_pages INTEGER DEFAULT 50,
                delay REAL DEFAULT 1.0
            )
        ''')
        
        # Create pages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pages (
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
                FOREIGN KEY (session_id) REFERENCES crawl_sessions (id)
            )
        ''')
        
        # Create links table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id INTEGER,
                url TEXT NOT NULL,
                text TEXT,
                is_internal BOOLEAN,
                FOREIGN KEY (page_id) REFERENCES pages (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def start_crawl(self, start_url, max_pages=50, delay=1.0):
        """Start a new crawling session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create new session
        cursor.execute('''
            INSERT INTO crawl_sessions (start_url, max_pages, delay)
            VALUES (?, ?, ?)
        ''', (start_url, max_pages, delay))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Start crawling in a separate thread
        thread = threading.Thread(target=self._crawl_worker, 
                                args=(session_id, start_url, max_pages, delay))
        thread.daemon = True
        thread.start()
        
        return session_id
    
    def _crawl_worker(self, session_id, start_url, max_pages, delay):
        """Worker function that performs the actual crawling"""
        visited = set()
        to_visit = deque([start_url])
        pages_crawled = 0
        
        base_domain = urlparse(start_url).netloc
        
        try:
            while to_visit and pages_crawled < max_pages:
                current_url = to_visit.popleft()
                
                if current_url in visited:
                    continue
                
                visited.add(current_url)
                
                # Crawl the page
                page_data = self._crawl_page(current_url, session_id)
                
                if page_data:
                    pages_crawled += 1
                    
                    # Extract links and add internal ones to queue
                    links = self._extract_links(page_data['content'], current_url, base_domain)
                    self._save_links(page_data['page_id'], links)
                    
                    # Add internal links to crawl queue
                    for link in links:
                        if link['is_internal'] and link['url'] not in visited:
                            to_visit.append(link['url'])
                
                # Respect delay
                time.sleep(delay)
                
                # Update session progress
                self._update_session_progress(session_id, pages_crawled)
        
        except Exception as e:
            print(f"Crawling error: {e}")
        
        finally:
            # Mark session as completed
            self._complete_session(session_id, pages_crawled)
    
    def _crawl_page(self, url, session_id):
        """Crawl a single page and return data"""
        try:
            start_time = time.time()
            response = self.session.get(url, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract page data
                title = soup.find('title')
                title = title.get_text().strip() if title else "No Title"
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                content = soup.get_text()
                content = re.sub(r'\s+', ' ', content).strip()
                
                word_count = len(content.split())
                link_count = len(soup.find_all('a', href=True))
                
                # Save to database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO pages (session_id, url, title, content, status_code, 
                                     response_time, word_count, link_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (session_id, url, title, content, response.status_code, 
                      response_time, word_count, link_count))
                
                page_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                return {
                    'page_id': page_id,
                    'url': url,
                    'title': title,
                    'content': response.content,
                    'status_code': response.status_code
                }
            
        except Exception as e:
            print(f"Error crawling {url}: {e}")
            return None
    
    def _extract_links(self, content, base_url, base_domain):
        """Extract links from page content"""
        soup = BeautifulSoup(content, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Skip invalid URLs
            if not full_url.startswith(('http://', 'https://')):
                continue
            
            parsed_url = urlparse(full_url)
            is_internal = parsed_url.netloc == base_domain
            
            links.append({
                'url': full_url,
                'text': link.get_text().strip()[:200],
                'is_internal': is_internal
            })
        
        return links
    
    def _save_links(self, page_id, links):
        """Save extracted links to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for link in links:
            cursor.execute('''
                INSERT INTO links (page_id, url, text, is_internal)
                VALUES (?, ?, ?, ?)
            ''', (page_id, link['url'], link['text'], link['is_internal']))
        
        conn.commit()
        conn.close()
    
    def _update_session_progress(self, session_id, pages_crawled):
        """Update session progress"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE crawl_sessions 
            SET total_pages = ?
            WHERE id = ?
        ''', (pages_crawled, session_id))
        
        conn.commit()
        conn.close()
    
    def _complete_session(self, session_id, total_pages):
        """Mark session as completed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE crawl_sessions 
            SET end_time = CURRENT_TIMESTAMP, status = 'completed', total_pages = ?
            WHERE id = ?
        ''', (total_pages, session_id))
        
        conn.commit()
        conn.close()
    
    def get_sessions(self):
        """Get all crawl sessions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, start_url, start_time, end_time, status, total_pages, max_pages
            FROM crawl_sessions
            ORDER BY start_time DESC
        ''')
        
        sessions = cursor.fetchall()
        conn.close()
        
        return [dict(zip(['id', 'start_url', 'start_time', 'end_time', 'status', 'total_pages', 'max_pages'], session)) for session in sessions]
    
    def get_session_pages(self, session_id):
        """Get pages for a specific session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, url, title, status_code, response_time, crawl_time, word_count, link_count
            FROM pages
            WHERE session_id = ?
            ORDER BY crawl_time DESC
        ''', (session_id,))
        
        pages = cursor.fetchall()
        conn.close()
        
        return [dict(zip(['id', 'url', 'title', 'status_code', 'response_time', 'crawl_time', 'word_count', 'link_count'], page)) for page in pages]