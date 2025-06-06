import unittest
from app import app

class SchedulerSprint1and2Tests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_hello_redirects_to_login(self):
        resp = self.client.get('/hello', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp.headers['Location'])

    def test_hello_test1_login(self):
        resp = self.client.get('/hello?user=test1', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        cookie = resp.headers.get('Set-Cookie')
        self.assertIn('session=', cookie)
        # Follow redirect with cookie
        resp2 = self.client.get('/hello', headers={'Cookie': cookie})
        self.assertIn(b'hello test1', resp2.data)

    def test_hello_test2_login_and_session_clear(self):
        resp = self.client.get('/hello?user=test2', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        cookie = resp.headers.get('Set-Cookie')
        self.assertIn('session=', cookie)
        resp2 = self.client.get('/hello', headers={'Cookie': cookie})
        self.assertIn(b'hello test2', resp2.data)

    def test_selections_get_post_get(self):
        # Login as test1
        resp = self.client.get('/footeam/selections?user=test1', follow_redirects=False)
        cookie = resp.headers.get('Set-Cookie')
        # GET (should be empty)
        resp2 = self.client.get('/footeam/selections', headers={'Cookie': cookie})
        self.assertEqual(resp2.json, [])
        # POST
        resp3 = self.client.post('/footeam/selections', headers={'Cookie': cookie, 'Content-Type': 'application/json'}, json=["M08","T09"])
        self.assertEqual(resp3.json['status'], 'ok')
        # GET again
        resp4 = self.client.get('/footeam/selections', headers={'Cookie': cookie})
        self.assertEqual(resp4.json, ["M08","T09"])

    def test_team_info(self):
        # test2
        resp = self.client.get('/footeam/selections?user=test2', follow_redirects=False)
        cookie2 = resp.headers.get('Set-Cookie')
        self.client.post('/footeam/selections', headers={'Cookie': cookie2, 'Content-Type': 'application/json'}, json=["M08","W10"])
        # test3
        resp = self.client.get('/footeam/selections?user=test3', follow_redirects=False)
        cookie3 = resp.headers.get('Set-Cookie')
        self.client.post('/footeam/selections', headers={'Cookie': cookie3, 'Content-Type': 'application/json'}, json=["F12","W10"])
        # GET info
        resp = self.client.get('/footeam/info')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['name'], 'footeam')
        self.assertIn('test1', data['users'])
        self.assertIn('test2', data['users'])
        self.assertIn('test3', data['users'])
        self.assertGreaterEqual(data['dayhours'].get('M08', 0), 1)
        self.assertGreaterEqual(data['dayhours'].get('W10', 0), 1)
        self.assertGreaterEqual(data['dayhours'].get('F12', 0), 1)

if __name__ == '__main__':
    unittest.main()
