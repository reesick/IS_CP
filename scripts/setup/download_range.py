"""Resumable HTTP range downloader for large official artifacts on slow links."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import time
import requests

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('output', type=Path)
    parser.add_argument('--workers', type=int, default=6)
    args = parser.parse_args()
    response = requests.head(args.url, allow_redirects=True, timeout=30)
    response.raise_for_status()
    total = int(response.headers['Content-Length'])
    chunk = 8 * 1024**2
    folder = args.output.with_suffix(args.output.suffix + '.parts')
    folder.mkdir(parents=True, exist_ok=True)
    def fetch(index):
        start = index * chunk
        end = min(total, start + chunk) - 1
        path = folder / str(index)
        if path.exists() and path.stat().st_size == end - start + 1:
            return index
        for attempt in range(4):
            try:
                result = requests.get(args.url, headers={'Range': f'bytes={start}-{end}'}, timeout=90)
                result.raise_for_status()
                expected_range = f'bytes {start}-{end}/{total}'
                if result.status_code != 206 or len(result.content) != end - start + 1 or result.headers.get('Content-Range') != expected_range:
                    raise RuntimeError('Server did not return requested byte range')
                path.write_bytes(result.content)
                return index
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(attempt + 1)
    count = (total + chunk - 1) // chunk
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(fetch, index) for index in range(count)]
        for completed, future in enumerate(as_completed(futures), 1):
            future.result()
            if completed % 10 == 0 or completed == count:
                print(f'{completed}/{count} chunks ({min(total, completed * chunk) / 1024**2:.0f} MiB)', flush=True)
    with args.output.open('wb') as output:
        for index in range(count):
            with (folder / str(index)).open('rb') as source:
                while data := source.read(1024**2):
                    output.write(data)
    assert args.output.stat().st_size == total
    print(f'Completed {args.output.name}: {total} bytes', flush=True)

if __name__ == '__main__':
    main()
