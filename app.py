from flask import Flask, render_template, request, send_file
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import io

app = Flask(__name__)

def get_chapter_text(session, url, headers):
    response = session.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    chapter_text = '\n'.join(p.text for p in soup.find(id='honbun').find_all('p'))
    return chapter_text

def get_novel_txt(novel_url: str):
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
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(
                    get_chapter_text, 
                    session, 
                    f'{novel_url}{i+1}.html', 
                    headers
                )
                for i in range(chapter_count)
            ]
            
            txt_data = '\n'.join(future.result() for future in concurrent.futures.as_completed(futures))
    
    return [txt_data, title]

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

if __name__ == '__main__':
    app.run(debug=False)