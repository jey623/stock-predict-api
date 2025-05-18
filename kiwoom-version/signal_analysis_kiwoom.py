127.0.0.1 - - [18/May/2025:07:35:58 +0000] "HEAD / HTTP/1.1" 500 0 "-" "Go-http-client/1.1"
UnicodeEncodeError: 'utf-8' codec can't encode characters in position 0-1: surrogates not allowed
            ^^^^^^^^^^^^^^
    value = value.encode()
  File "/opt/render/project/src/.venv/lib/python3.11/site-packages/werkzeug/wrappers/response.py", line 297, in set_data
    self.set_data(response)
  File "/opt/render/project/src/.venv/lib/python3.11/site-packages/werkzeug/wrappers/response.py", line 175, in __init__
         ^^^^^^^^^^^^^^^^^^^^
    rv = self.response_class(
  File "/opt/render/project/src/.venv/lib/python3.11/site-packages/flask/app.py", line 1224, in make_response
               ^^^^^^^^^^^^^^^^^^^^^^
    response = self.make_response(rv)
  File "/opt/render/project/src/.venv/lib/python3.11/site-packages/flask/app.py", line 939, in finalize_request
           ^^^^^^^^^^^^^^^^^^^^^^^^^
    return self.finalize_request(rv)
  File "/opt/render/project/src/.venv/lib/python3.11/site-packages/flask/app.py", line 920, in full_dispatch_request
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    response = self.full_dispatch_request()
  File "/opt/render/project/src/.venv/lib/python3.11/site-packages/flask/app.py", line 1511, in wsgi_app
Traceback (most recent call last):
[2025-05-18 07:35:58,134] ERROR in app: Exception on / [HEAD]
==> Your service is live 🎉
[2025-05-18 07:35:57 +0000] [93] [INFO] Booting worker with pid: 93
[2025-05-18 07:35:57 +0000] [85] [INFO] Using worker: sync
[2025-05-18 07:35:57 +0000] [85] [INFO] Listening at: http://0.0.0.0:10000 (85)
[2025-05-18 07:35:57 +0000] [85] [INFO] Starting gunicorn 23.0.0
==> Running 'gunicorn signal_analysis_kiwoom:app --bind 0.0.0.0:10000'
==> Deploying...
==> Build successful 🎉
==> Uploaded in 4.9s. Compression took 1.5s
==> Uploading build...
[notice] To update, run: pip install --upgrade pip
[notice] A new release of pip is available: 24.0 -> 25.1.1
Successfully installed blinker-1.9.0 certifi-2025.4.26 charset-normalizer-3.4.2 click-8.2.0 flask-3.1.1 gunicorn-23.0.0 idna-3.10 itsdangerous-2.2.0 jinja2-3.1.6 markupsafe-3.0.2 numpy-2.2.6 packaging-25.0 pandas-2.2.3 python-dateutil-2.9.0.post0 pytz-2025.2 requests-2.32.3 six-1.17.0 ta-0.11.0 tzdata-2025.2 urllib3-2.4.0 werkzeug-3.1.3
Installing collected packages: pytz, urllib3, tzdata, six, packaging, numpy, markupsafe, itsdangerous, idna, click, charset-normalizer, certifi, blinker, werkzeug, requests, python-dateutil, jinja2, gunicorn, pandas, flask, ta
Using cached six-1.17.0-py2.py3-none-any.whl (11 kB)
Using cached packaging-25.0-py3-none-any.whl (66 kB)
Using cached werkzeug-3.1.3-py3-none-any.whl (224 kB)
Using cached urllib3-2.4.0-py3-none-any.whl (128 kB)
Using cached tzdata-2025.2-py2.py3-none-any.whl (347 kB)
Using cached pytz-2025.2-py2.py3-none-any.whl (509 kB)
Using cached python_dateutil-2.9.0.post0-py2.py3-none-any.whl (229 kB)
Using cached numpy-2.2.6-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (16.8 MB)
Using cached MarkupSafe-3.0.2-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (23 kB)
Using cached jinja2-3.1.6-py3-none-any.whl (134 kB)
Using cached itsdangerous-2.2.0-py3-none-any.whl (16 kB)
Using cached idna-3.10-py3-none-any.whl (70 kB)
Using cached click-8.2.0-py3-none-any.whl (102 kB)
Using cached charset_normalizer-3.4.2-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (147 kB)
Using cached certifi-2025.4.26-py3-none-any.whl (159 kB)
Using cached blinker-1.9.0-py3-none-any.whl (8.5 kB)
Using cached gunicorn-23.0.0-py3-none-any.whl (85 kB)
Using cached requests-2.32.3-py3-none-any.whl (64 kB)
Using cached pandas-2.2.3-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (13.1 MB)
Using cached flask-3.1.1-py3-none-any.whl (103 kB)
  Using cached six-1.17.0-py2.py3-none-any.whl.metadata (1.7 kB)
Collecting six>=1.5 (from python-dateutil>=2.8.2->pandas->-r requirements.txt (line 2))
  Using cached packaging-25.0-py3-none-any.whl.metadata (3.3 kB)
Collecting packaging (from gunicorn->-r requirements.txt (line 5))
  Using cached certifi-2025.4.26-py3-none-any.whl.metadata (2.5 kB)
Collecting certifi>=2017.4.17 (from requests->-r requirements.txt (line 4))
  Using cached urllib3-2.4.0-py3-none-any.whl.metadata (6.5 kB)
Collecting urllib3<3,>=1.21.1 (from requests->-r requirements.txt (line 4))
  Using cached idna-3.10-py3-none-any.whl.metadata (10 kB)
Collecting idna<4,>=2.5 (from requests->-r requirements.txt (line 4))
  Using cached charset_normalizer-3.4.2-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (35 kB)
Collecting charset-normalizer<4,>=2 (from requests->-r requirements.txt (line 4))
  Using cached tzdata-2025.2-py2.py3-none-any.whl.metadata (1.4 kB)
Collecting tzdata>=2022.7 (from pandas->-r requirements.txt (line 2))
  Using cached pytz-2025.2-py2.py3-none-any.whl.metadata (22 kB)
Collecting pytz>=2020.1 (from pandas->-r requirements.txt (line 2))
  Using cached python_dateutil-2.9.0.post0-py2.py3-none-any.whl.metadata (8.4 kB)
Collecting python-dateutil>=2.8.2 (from pandas->-r requirements.txt (line 2))
  Using cached numpy-2.2.6-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (62 kB)
Collecting numpy>=1.23.2 (from pandas->-r requirements.txt (line 2))
  Using cached werkzeug-3.1.3-py3-none-any.whl.metadata (3.7 kB)
Collecting werkzeug>=3.1.0 (from flask->-r requirements.txt (line 1))
  Using cached MarkupSafe-3.0.2-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (4.0 kB)
Collecting markupsafe>=2.1.1 (from flask->-r requirements.txt (line 1))
  Using cached jinja2-3.1.6-py3-none-any.whl.metadata (2.9 kB)
Collecting jinja2>=3.1.2 (from flask->-r requirements.txt (line 1))
  Using cached itsdangerous-2.2.0-py3-none-any.whl.metadata (1.9 kB)
Collecting itsdangerous>=2.2.0 (from flask->-r requirements.txt (line 1))
  Using cached click-8.2.0-py3-none-any.whl.metadata (2.5 kB)
Collecting click>=8.1.3 (from flask->-r requirements.txt (line 1))
  Using cached blinker-1.9.0-py3-none-any.whl.metadata (1.6 kB)
Collecting blinker>=1.9.0 (from flask->-r requirements.txt (line 1))
  Using cached gunicorn-23.0.0-py3-none-any.whl.metadata (4.4 kB)
Collecting gunicorn (from -r requirements.txt (line 5))
  Using cached requests-2.32.3-py3-none-any.whl.metadata (4.6 kB)
Collecting requests (from -r requirements.txt (line 4))
  Using cached ta-0.11.0-py3-none-any.whl
Collecting ta (from -r requirements.txt (line 3))
  Using cached pandas-2.2.3-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (89 kB)
Collecting pandas (from -r requirements.txt (line 2))
  Using cached flask-3.1.1-py3-none-any.whl.metadata (3.0 kB)
Collecting flask (from -r requirements.txt (line 1))
==> Running build command 'pip install -r requirements.txt'...
==> Docs on specifying a Poetry version: https://render.com/docs/poetry-version
==> Using Poetry version 1.7.1 (default)
==> Docs on specifying a Python version: https://render.com/docs/python-version
==> Using Python version 3.11.11 (default)
==> Transferred 138MB in 7s. Extraction took 3s.
==> Downloading cache...
==> Checking out commit 43cae0d8a177df64669b2dc16ce553f641e7da07 in branch main
==> Cloning from https://github.com/jey623/stock-predict-api
