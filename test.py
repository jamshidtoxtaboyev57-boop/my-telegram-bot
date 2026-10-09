import urllib.request
import json
import time

def test_search(query="eminem"):
    start = time.time()
    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&media=music&limit=10"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read())
        
    results = data.get('results', [])
    print(f"Time: {time.time() - start:.3f}s")
    print(f"Found: {len(results)}")
    for r in results[:2]:
        print(r.get('trackId'), r.get('trackName'), r.get('artistName'), r.get('trackTimeMillis'))

if __name__ == "__main__":
    import urllib.parse
    test_search()
