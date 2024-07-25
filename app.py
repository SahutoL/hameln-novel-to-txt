from flask import Flask, render_template, request, send_file, jsonify, send_from_directory
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib.parse import urlencode
from bs4 import BeautifulSoup
import concurrent.futures
from time import sleep
import threading, io, re, random

app = Flask(__name__)

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
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    ]
    return random.choice(user_agents)


def get_chapter_text(session, url, headers, retry_count=3):
    for _ in range(retry_count):
        try:
            response = session.get(url, headers=headers, cookies={'over18':'off'})
            soup = BeautifulSoup(response.text, "html.parser")
            chapter_text = '\n'.join(p.text for p in soup.find(id='honbun').find_all('p'))
            return chapter_text
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}. Retrying...")
            sleep(1)
    return ""

def get_novel_txt(novel_url: str, nid: str):
    novel_url = novel_url.rstrip('/') + '/'
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    }

    with get_session() as session:
        response = session.get(novel_url, headers=headers, cookies={'over18':'off'})
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.find('div', class_='ss').find('span', attrs={'itemprop':'name'}).text
        chapter_count = len(soup.select('a[href^="./"]'))

        txt_data = [None] * chapter_count

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {executor.submit(get_chapter_text, session, f'{novel_url}{i+1}.html', headers): i for i in range(chapter_count)}
            for future in concurrent.futures.as_completed(future_to_url):
                chapter_num = future_to_url[future] + 1
                try:
                    chapter_text = future.result()
                    txt_data[chapter_num] = chapter_text
                    progress_store[nid] = int((chapter_num / chapter_count) * 100)
                except Exception as exc:
                    print(f'Chapter {chapter_num} generated an exception: {exc}')

        novel_text = '\n\n'.join(filter(None, txt_data))
        novel_store[nid] = [novel_text, title]
        progress_store[nid] = 100

def start_scraping_task(url, nid):
    get_novel_txt(url, nid)
    if nid in background_tasks:
        del background_tasks[nid]

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/start-scraping', methods=['POST'])
def start_scraping():
    url = request.json['url']
    match = re.search(r'https://syosetu.org/novel/(\d+)/', url)
    if match:
        nid = match.group(1)
        novel_url = f"https://syosetu.org/novel/{nid}/"
        try:
            # Start the scraping process in a background thread
            task = threading.Thread(target=start_scraping_task, args=(novel_url, nid))
            task.start()
            background_tasks[nid] = task
            return jsonify({"status": "started", "nid": nid})
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    else:
        return jsonify({"error": "Invalid URL format. Please enter a valid URL."}), 400

@app.route('/progress/<nid>', methods=['GET'])
def get_progress(nid):
    progress = progress_store.get(nid, 0)
    return jsonify({"progress": progress})

@app.route('/download/<nid>', methods=['GET'])
def download_novel(nid):
    novel_text, title = novel_store.get(nid)
    if novel_text:
        buffer = io.BytesIO()
        buffer.write(novel_text.encode('utf-8'))
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f'{title}.txt', mimetype='text/plain')
    else:
        return jsonify({"error": "Novel not found or scraping not completed"}), 404

@app.route('/search', methods=['POST'])
def search():
    word = request.form.get('word', '')
    checkedR18 = request.form.get('mode', 'search')
    parody = request.form.get('parody', '')
    type_value = request.form.get('type', '0')

    filter_params = ['mozi2', 'mozi1', 'mozi2_all', 'mozi1_all', 'rate2', 'rate1', 
                     'soupt2', 'soupt1', 'f2', 'f1', 're2', 're1', 'v2', 'v1', 
                     'r2', 'r1', 't2', 't1']

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
    }
    with get_session() as session:
        try:
            response = session.get(url, headers=headers, cookies={'over18':'off', 'list_num':'50'})
            soup = BeautifulSoup(response.text, 'html.parser')
            novels = soup.find_all('div', class_='section3')

            results = []
            for novel in novels:
                title = novel.find('a').text
                link = novel.find('a').get('href')
                author = novel.find_all('a')[2].text
                parody = novel.find_all('a')[1].text
                description = novel.find('div', class_='blo_inword').text
                results.append({'title': title, 'link': link, 'author': author, 'parody': parody, 'description': description})
            return jsonify({'results': results})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('static', 'service-worker.js')

if __name__ == '__main__':
    app.run(debug=False)
