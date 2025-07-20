
# 🕷️ Spidey: The Web Crawler

Spidey is a lightweight, extensible Python-based web crawler built for rapid deployment and real-time data extraction. It supports intelligent link-following, language detection, readability scoring, duplicate content detection, and structured data export — all with a simple SQLite backend.

<img width="1363" height="768" alt="image" src="https://github.com/user-attachments/assets/4dda8e84-e745-449a-a9c4-2a0c15ff9baa" />


---

## 🚀 Features

- 🔗 Extracts and follows internal links
- 🧠 Detects language and readability of pages
- 🧹 Cleans HTML to extract useful content
- 📄 Stores pages, links, and sessions in SQLite
- 📦 Exports data as JSON
- 🔍 Relative link support (e.g., Wikipedia)
- 🧵 Multithreaded crawling

---

## 📦 Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

---

## 🛠️ Usage

### Run the crawler:

```bash
python database_schema.py
python app.py
```

It will start a crawl from the given URL and save the session to the SQLite database.

---

## ⚙️ Project Structure

```
Spidey-The-Web-Crawler/
│
├── crawler.py             # Main crawler logic
├── app.py 
├── requirements.txt       # Python dependencies
├── database/              # SQLite database file
    |
    ├──crawler.db
├── exports/               # JSON export output
├── static/              
    |
    ├──script.js
    ├──style.css
├── templates/              
    |
    ├──index.html
├── LICENSE
└── README.md              
```

---

## 🧠 Future Ideas

- Export to CSV
- Add media/video/document crawling
- Frontend for live progress (Flask/UI)
- Scheduler to auto-run crawls

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file.

---

## 💬 Feedback

Found a bug? Have a feature request? Open an [issue](https://github.com/hridyansh5492/Spidey-The-Web-Crawler/issues) or drop a ⭐ if you like the project!
