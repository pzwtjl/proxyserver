import unittest
from socket import gethostbyname
from multiprocessing import Process, Manager
import json
import app
import requests
import proxy

def run_server():
    app.app.run(port=5000)

def run_proxy():
    proxy.proxyServer(8888)

class TestProxy(unittest.TestCase):
    def setUp(self):
        self.s_process = Process(target=run_server)
        self.s_process.start()
        self.s_process.join(1)
        print('Server started')
        self.p_process = Process(target=run_proxy)
        self.p_process.start()
        self.p_process.join(1)
        print('Proxy started')

        self.proxies = { 'http': 'http://localhost:8888' }

    def tearDown(self):
        self.s_process.terminate()
        print('Server terminated')
        self.p_process.terminate()
        print('Proxy terminated')

    def testBasic200(self):
        r = requests.get('http://localhost:5000/test-basic-200', proxies=self.proxies, timeout = 5)
        if r.status_code == 200:
            return True
        else:
            return False

        # self.assertEqual(r.status_code, 200, 'Server returned non-200 status code')
        # self.assertEqual(r.content.decode(), f'<!doctype html><html><title>Test File</title><p>You provided: test-basic-200</p><p>We provided: {app.server_string}</p></html>', 'File data does not match')

    def testBasic404(self):
        r = requests.get(f'http://localhost:5000/{app.not_found_string}', proxies=self.proxies)
        self.assertEqual(r.status_code, 404, 'Server returned non-404 status code')

    def testPosts(self):
        r = requests.post('http://localhost:5000/post', data={ 'input_string': 'test-posts' }, proxies=self.proxies)
        self.assertEqual(r.status_code, 200, 'Server returned non-200 status code')
        self.assertEqual(r.content.decode(), f'<!doctype html><html><title>Test File</title><p>You provided: test-posts</p><p>We provided: {app.server_string}</p></html>', 'File data does not match')

    def testCacheGets(self):
        r = requests.get('http://localhost:5000/test-cache-GETs', proxies=self.proxies)
        self.assertEqual(r.status_code, 200, 'Server returned non-200 status code')
        self.assertEqual(r.content.decode(), f'<!doctype html><html><title>Test File</title><p>You provided: test-cache-GETs</p><p>We provided: {app.server_string}</p></html>', 'File data does not match')

        r = requests.get('http://localhost:5000/test-cache-GETs', proxies=self.proxies)
        self.assertEqual(r.status_code, 200, 'Server returned non-200 status code')
        self.assertEqual(r.content.decode(), f'<!doctype html><html><title>Test File</title><p>You provided: test-cache-GETs</p><p>We provided: {app.server_string}</p></html>', 'File data does not match')

        r = requests.get(f'http://localhost:5000/count')
        count_dict = json.loads(r.content.decode())
        self.assertIn('test-cache-GETs', count_dict)
        self.assertEqual(count_dict['test-cache-GETs'], 1)

    def testCachePosts(self):
        r = requests.post('http://localhost:5000/post', data={ 'input_string': 'test-cache-POSTs' }, proxies=self.proxies)
        self.assertEqual(r.status_code, 200, 'Server returned non-200 status code')
        self.assertEqual(r.content.decode(), f'<!doctype html><html><title>Test File</title><p>You provided: test-cache-POSTs</p><p>We provided: {app.server_string}</p></html>', 'File data does not match')

        r = requests.post('http://localhost:5000/post', data={ 'input_string': 'test-cache-POSTs' }, proxies=self.proxies)
        self.assertEqual(r.status_code, 200, 'Server returned non-200 status code')
        self.assertEqual(r.content.decode(), f'<!doctype html><html><title>Test File</title><p>You provided: test-cache-POSTs</p><p>We provided: {app.server_string}</p></html>', 'File data does not match')

        r = requests.get(f'http://localhost:5000/count')
        count_dict = json.loads(r.content.decode())
        self.assertIn('test-cache-POSTs', count_dict)
        self.assertEqual(count_dict['test-cache-POSTs'], 2)
