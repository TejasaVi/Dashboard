from app import create_app
from flask import Flask, render_template, jsonify
from flask_cors import CORS

app = create_app()
CORS(app)   # allow all origins

if __name__ == "__main__":
    app.run(port=5000, debug=True)

