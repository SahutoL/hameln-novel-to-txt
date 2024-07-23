from flask import Flask, render_template, request, send_file, jsonify
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import io
import re
from time import sleep
from functools import partial

app = Flask(__name__)

def get_chapter_text(session, url, headers, retry_count=3):
    for _ in range(retry_count):
        try:
            response = session.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")
            chapter_text = '\n'.join(p.text for p in soup.find(id='honbun').find_all('p'))
            return chapter_text
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}. Retrying...")
            sleep(1)
    return ""

def get_novel_txt(novel_url: str, progress_callback=None):
    novel_url = novel_url.rstrip('/') + '/'
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    }
    
    with requests.Session() as session:
        response = session.get(novel_url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.find('div', class_='ss').find('a').text
        chapter_count = len(soup.select('a[href^="./"]'))
        
        txt_data = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {executor.submit(get_chapter_text, session, f'{novel_url}{i+1}.html', headers): i for i in range(chapter_count)}
            for future in concurrent.futures.as_completed(future_to_url):
                chapter_num = future_to_url[future] + 1
                try:
                    chapter_text = future.result()
                    txt_data.append(chapter_text)
                    if progress_callback:
                        progress_callback(chapter_num, chapter_count)
                except Exception as exc:
                    print(f'Chapter {chapter_num} generated an exception: {exc}')
        
        return ['\n\n'.join(txt_data), title]

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['nid']
        match = re.search(r'https://syosetu.org/novel/(\d+)/', url)
        if match:
            nid = match.group(1)
            novel_url = f"https://syosetu.org/novel/{nid}/"
            try:
                novel_text, title = get_novel_txt(novel_url)
                buffer = io.BytesIO()
                buffer.write(novel_text.encode('utf-8'))
                buffer.seek(0)
                return send_file(buffer, as_attachment=True, download_name=f'{title}.txt', mimetype='text/plain')
            except Exception as e:
                return render_template('index.html', error=str(e))
        else:
            return render_template('index.html', error="Invalid URL format. Please enter a valid URL.")
    return render_template('index.html')

@app.route('/start-scraping', methods=['POST'])
def start_scraping():
    url = request.json['url']
    match = re.search(r'https://syosetu.org/novel/(\d+)/', url)
    if match:
        nid = match.group(1)
        novel_url = f"https://syosetu.org/novel/{nid}/"
        try:
            executor.submit(partial(get_novel_txt, novel_url, progress_callback=update_progress))
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
    novel_text = novel_store.get(nid)
    if novel_text:
        buffer = io.BytesIO()
        buffer.write(novel_text.encode('utf-8'))
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f'novel_{nid}.txt', mimetype='text/plain')
    else:
        return jsonify({"error": "Novel not found or scraping not completed"}), 404


progress_store = {}
novel_store = {}

def update_progress(chapter, total_chapters, nid):
    progress = int((chapter / total_chapters) * 100)
    progress_store[nid] = progress

if __name__ == '__main__':
    app.run(debug=True)