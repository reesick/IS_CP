"""Exercise the running local API without submitting an expensive GPU job."""
import argparse
import json
import urllib.request

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    for route in ['/api/v1/health', '/api/v1/capabilities']:
        with urllib.request.urlopen(args.base_url + route, timeout=20) as response:
            payload = json.load(response)
            print(json.dumps({'route': route, 'status': response.status, 'result': payload}, indent=2))
    with urllib.request.urlopen(args.base_url, timeout=20) as response:
        assert response.status == 200 and b'ImageShield' in response.read()
    print('CPU API and frontend smoke passed. This does not measure protection efficacy.')

if __name__ == '__main__':
    main()
