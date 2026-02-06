#!/usr/bin/env python3
"""
Simple CORS proxy for GraphDB
Usage: python proxy.py
Then change CONFIG.graphdb.url to http://localhost:8001
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json

GRAPHDB_URL = "http://localhost:7200"

class ProxyHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
        self.end_headers()
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        
        # Forward to GraphDB
        url = GRAPHDB_URL + self.path
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                'Content-Type': self.headers['Content-Type'],
                'Accept': 'application/sparql-results+json'
            }
        )
        
        try:
            response = urllib.request.urlopen(req)
            data = response.read()
            
            # Send response with CORS headers
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/sparql-results+json')
            self.end_headers()
            self.wfile.write(data)
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

if __name__ == '__main__':
    server = HTTPServer(('localhost', 8001), ProxyHandler)
    print("🔗 CORS Proxy running on http://localhost:8001")
    print("📊 Forwarding to GraphDB at http://localhost:7200")
    print("Press Ctrl+C to stop")
    server.serve_forever()
