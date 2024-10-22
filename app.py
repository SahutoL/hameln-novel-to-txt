from flask import Flask, render_template, request, send_file, jsonify, send_from_directory
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib.parse import urlencode
from bs4 import BeautifulSoup
import concurrent.futures
from time import sleep
import threading, io, os, re, random, logging
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('LoggingTest')
sh = logging.StreamHandler()
logger.addHandler(sh)
logger.setLevel(logging.INFO)

class Novel(Base):
    __tablename__ = 'novels'
    id = Column(Integer, primary_key=True)
    nid = Column(String, unique=True, nullable=False)
    novel_text = Column(Text)
    title = Column(String)

Base.metadata.create_all(engine)

progress_store = {}
novel_store = {}
background_tasks = {}

def get_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]
    return random.choice(user_agents)

def get_random_referer():
    referers = [
        "https://www.google.com/search?q=%E3%83%8F%E3%83%BC%E3%83%A1%E3%83%AB%E3%83%B3&ie=UTF-8&oe=UTF-8&hl=ja-jp&client=safari",
        "https://syosetu.org/",
        "https://syosetu.org/search/?mode=search",
        "https://syosetu.org/?mode=rank",
        "https://syosetu.org/?mode=favo"
    ]
    return random.choice(referers)

def get_random_delay():
    return random.uniform(5, 10)

def get_chapter_text(session, url, headers, retry_count=3):
    for _ in range(retry_count):
        try:
            sleep(get_random_delay())
            response = session.get(url, headers=headers, cookies={'over18':'off'})
            soup = BeautifulSoup(response.text, "html.parser")
            chapter_text = '\n'.join(p.text for p in soup.find(id='honbun').find_all('p'))
            return chapter_text
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}. Retrying...")
            sleep(get_random_delay())
    return ""


def get_novel_txt(novel_url: str, nid: str):
    novel_url = novel_url.rstrip('/') + '/'
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ja-JP,ja;q=0.9",
        "Referer": get_random_referer(),
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive"
    }

    with get_session() as session:
        sleep(get_random_delay())
        response = session.get(novel_url, headers=headers, cookies={'over18':'off'})
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.find('div', class_='ss').find('span', attrs={'itemprop':'name'}).text
        chapter_count = len(soup.select('a[href^="./"]'))

        txt_data = [None] * chapter_count

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future_to_url = {executor.submit(get_chapter_text, session, f'{novel_url}{i+1}.html', headers): i for i in range(chapter_count)}
            completed_chapters = 0
            for future in concurrent.futures.as_completed(future_to_url):
                chapter_num = future_to_url[future] + 1
                try:
                    chapter_text = future.result()
                    txt_data[chapter_num] = chapter_text
                    completed_chapters += 1
                    progress_store[nid] = int((completed_chapters / chapter_count) * 100)
                except Exception as exc:
                    print(f'Chapter {chapter_num} generated an exception: {exc}')

        novel_text = '\n\n'.join(filter(None, txt_data))
        novel_store[nid] = [novel_text, title]
        progress_store[nid] = 100
        
        session = Session()
        novel = Novel(nid=nid, novel_text=novel_text, title=title)
        session.add(novel)
        session.commit()
        session.close()

def get_all_chapter_urls(session, novel_url, headers):
    chapter_urls = []
    page_num = 1

    while True:
        url = f"{novel_url}?p={page_num}"
        sleep(get_random_delay())
        response = session.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        chapter_links = soup.select('a[href^="/{}/"]'.format(novel_url.split('/')[-2]))
        if not chapter_links:
            break

        for link in chapter_links:
            chapter_urls.append(novel_url.rstrip('/') + link['href'])

        next_page = soup.find('a', text='次へ')
        if not next_page:
            break

        page_num += 1

    return chapter_urls


def get_narou_novel_txt(novel_url: str, nid: str):
    novel_url = novel_url.rstrip('/') + '/'
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ja-JP,ja;q=0.9",
        "Referer": get_random_referer(),
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive"
    }

    with get_session() as session:
        sleep(get_random_delay())
        response = session.get(novel_url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        title_tag = soup.find('p', class_='novel_title')
        if title_tag:
            title = title_tag.text.strip()
        else:
            title = 'No Title'

        chapter_links = []
        toc_area = soup.find('div', id='novel_no')
        if toc_area:
            chapter_links.append(novel_url)
        else:
            def collect_chapter_links(soup):
                for dd in soup.find_all('dd', class_='subtitle'):
                    a = dd.find('a')
                    if a:
                        href = a.get('href')
                        if href:
                            chapter_url = urllib.parse.urljoin(novel_url, href)
                            chapter_links.append(chapter_url)

            collect_chapter_links(soup)

            page_nav = soup.find('div', class_='index_box')
            if page_nav:
                page_links = page_nav.find_all('a', class_='next_page')
                while page_links:
                    next_page_url = urllib.parse.urljoin(novel_url, page_links[0].get('href'))
                    sleep(get_random_delay())
                    response = session.get(next_page_url, headers=headers)
                    soup = BeautifulSoup(response.text, "html.parser")
                    collect_chapter_links(soup)
                    page_nav = soup.find('div', class_='index_box')
                    if page_nav:
                        page_links = page_nav.find_all('a', class_='next_page')
                    else:
                        break

        chapter_count = len(chapter_links)
        txt_data = [None] * chapter_count

        def fetch_chapter(chapter_url, index):
            for _ in range(3):
                try:
                    sleep(get_random_delay())
                    response = session.get(chapter_url, headers=headers)
                    soup = BeautifulSoup(response.text, "html.parser")
                    honbun = soup.find('div', id='novel_honbun')
                    if honbun:
                        chapter_text = '\n'.join(p.text for p in honbun.find_all('p'))
                        return chapter_text
                except Exception as e:
                    print(f"Error fetching {chapter_url}: {str(e)}. Retrying...")
                    sleep(get_random_delay())
            return ""

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future_to_index = {executor.submit(fetch_chapter, chapter_links[i], i): i for i in range(chapter_count)}
            completed_chapters = 0
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    chapter_text = future.result()
                    txt_data[index] = chapter_text
                    completed_chapters += 1
                    progress_store[nid] = int((completed_chapters / chapter_count) * 100)
                except Exception as exc:
                    print(f'Chapter {index+1} generated an exception: {exc}')

        novel_text = '\n\n'.join(filter(None, txt_data))
        novel_store[nid] = [novel_text, title]
        progress_store[nid] = 100

        session_db = Session()
        novel = Novel(nid=nid, novel_text=novel_text, title=title)
        session_db.add(novel)
        session_db.commit()
        session_db.close()

def start_scraping_task(url, nid, site):
    if site == 'syosetu_org':
        get_novel_txt(url, nid)
    elif site == 'ncode_syosetu_com':
        get_narou_novel_txt(url, nid)
    if nid in background_tasks:
        del background_tasks[nid]

def parse_novel(novel):
    title = novel.find('a').text
    link = novel.find('a').get('href')
    author_info = novel.find_all('div', class_='blo_title_sak')[-1].text.split('\n')
    author = author_info[2][2:]
    parody = author_info[1].replace('原作：','').replace('オリジナル：','')
    description = novel.find('div', class_='blo_inword').text
    status = novel.find('div', class_='blo_wasuu_base').find('span').text
    latest = novel.find('a', attrs={'title':'最新話へのリンク'}).text
    updated_day = novel.find('div', attrs={'title':'最終更新日'}).text
    words = novel.find('div', attrs={'title': '総文字数'}).text.split(' ')[1]
    evaluation = novel.find('div', class_='blo_hyouka').text.strip()[5:]
    all_keywords = novel.find('div', class_='all_keyword').find_all('a')
    alert_keywords = [x.text for x in novel.find('div', class_='all_keyword').find('span').find_all('a')]
    keywords = [x.text for x in all_keywords if x.text not in alert_keywords]
    favs = novel.find_all('div', attrs={'style': 'background-color: transparent;'})[-1].text.split('｜')[1][6:]

    return {
        'title': title,
        'link': link,
        'author': author,
        'parody': parody,
        'description': description,
        'status': status,
        'latest': latest,
        'updated_day': f'{updated_day[:10]} {updated_day[10:]}',
        'words': words,
        'evaluation': evaluation,
        'alert_keywords': alert_keywords,
        'keywords': keywords,
        'favs': favs
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/start-scraping', methods=['POST'])
def start_scraping():
    url = request.json['url']
    match_syosetu = re.search(r'https://syosetu.org/novel/(\d+)/', url)
    match_ncode = re.search(r'https://ncode.syosetu.com/([a-z0-9]+)/?', url)
    
    if match_syosetu:
        nid = match_syosetu.group(1)
        novel_url = f"https://syosetu.org/novel/{nid}/"
        site = 'syosetu_org'
    elif match_ncode:
        nid = match_ncode.group(1)
        novel_url = f"https://ncode.syosetu.com/{nid}/"
        site = 'ncode_syosetu_com'
    else:
        return jsonify({"error": "Invalid URL format. Please enter a valid URL."}), 400
    
    session = Session()
    existing_novel = session.query(Novel).filter_by(nid=nid).first()
    session.close()

    if existing_novel:
        novel_store[nid] = [existing_novel.novel_text, existing_novel.title]
        progress_store[nid] = 100
        return jsonify({"status": "ready", "nid": nid})
    else:
        try:
            task = threading.Thread(target=start_scraping_task, args=(novel_url, nid, site))
            task.start()
            background_tasks[nid] = task
            return jsonify({"status": "started", "nid": nid})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

@app.route('/progress/<nid>', methods=['GET'])
def get_progress(nid):
    progress = progress_store.get(nid, 0)
    return jsonify({"progress": progress})

@app.route('/download/<nid>', methods=['GET'])
def download_novel(nid):
    session = Session()
    novel = session.query(Novel).filter_by(nid=nid).first()
    session.close()

    if novel:
        buffer = io.BytesIO()
        buffer.write(novel.novel_text.encode('utf-8'))
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f'{novel.title}.txt', mimetype='text/plain')
    else:
        return jsonify({"error": "Novel not found or scraping not completed"}), 404

@app.route('/search', methods=['POST'])
def search():
    word = request.form.get('word', '')
    checkedR18 = request.form.get('mode', 'search')
    parody = request.form.get('parody', '')
    type_value = request.form.get('type', '0')

    filter_params = ['rensai_s1', 'rensai_s2', 'rensai_s4', 'mozi2', 'mozi1', 'mozi2_all', 'mozi1_all', 'rate2', 'rate1', 
                     'soupt2', 'soupt1', 'f2', 'f1', 're2', 're1', 'v2', 'v1', 
                     'r2', 'r1', 't2', 't1', 'd2', 'd1']

    url_params = {
        'mode': checkedR18,
        'word': word,
        'gensaku': parody,
        'type': type_value
    }

    for param in filter_params:
        value = request.form.get(param)
        if value:
            url_params[param] = value

    base_url = "https://syosetu.org/search/"
    url = f"{base_url}?{urlencode(url_params)}"

    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ja-JP,ja;q=0.9",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1"
    }
    with get_session() as session:
        try:
            sleep(random.uniform(2,4))
            response = session.get(url, headers=headers, cookies={'over18':'off', 'list_num':'50'})
            soup = BeautifulSoup(response.text, 'html.parser')
            novels = soup.find_all('div', class_='section3')

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_index = {executor.submit(parse_novel, novel): i for i, novel in enumerate(novels)}
                results = [None] * len(novels)
                
                for future in concurrent.futures.as_completed(future_to_index):
                    index = future_to_index[future]
                    results[index] = future.result()

            return jsonify({'results': results})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('static', 'service-worker.js')

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml')

if __name__ == '__main__':
    app.run(debug=False)