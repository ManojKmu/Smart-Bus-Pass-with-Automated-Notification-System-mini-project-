"""
Smart Bus Mobile-Optimized Server
Fixes: HTTP errors, security warnings, slow loading
"""
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, make_response
import random
import smtplib
from email.mime.text import MIMEText
import os
import datetime
import json
import socket
from functools import wraps
import gzip
from io import BytesIO

app = Flask(__name__, template_folder='templates', static_folder='static')

# ========== MOBILE PERFORMANCE OPTIMIZATIONS ==========

# 1. Enable response compression for faster mobile loading
def gzip_response(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        
        # Check if client accepts gzip
        accept_encoding = request.headers.get('Accept-Encoding', '')
        
        if 'gzip' not in accept_encoding.lower():
            return response
        
        # Compress response
        if response.status_code < 200 or response.status_code >= 300:
            return response
            
        gzip_buffer = BytesIO()
        gzip_file = gzip.GzipFile(mode='wb', fileobj=gzip_buffer)
        gzip_file.write(response.get_data())
        gzip_file.close()
        
        response.set_data(gzip_buffer.getvalue())
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = len(response.get_data())
        
        return response
    return decorated_function

# 2. Aggressive caching for static files
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year
app.config['JSON_SORT_KEYS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = False  # Disable for speed

# 3. Disable debug logging for speed
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# ========== DATA STORAGE ==========
otp_store = {}
user_passes_db = {}

#