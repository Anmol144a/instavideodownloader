from flask import Flask, request, render_template, send_file, jsonify
import instaloader
import os
import shutil
from datetime import datetime
import re

app = Flask(__name__, template_folder='')  # Disable default templates folder, look in current directory

# Directory to store downloaded videos temporarily
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Initialize Instaloader
L = instaloader.Instaloader()

# Function to clean up old files
def cleanup_downloads():
    for filename in os.listdir(DOWNLOAD_DIR):
        file_path = os.path.join(DOWNLOAD_DIR, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Error cleaning up {file_path}: {e}")

# Function to extract shortcode from Instagram URL
def get_shortcode(url):
    pattern = r'instagram\.com/(?:p|reel)/([A-Za-z0-9_-]+)/?'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    if not url:
        return jsonify({'error': 'Please provide an Instagram post URL'}), 400

    shortcode = get_shortcode(url)
    if not shortcode:
        return jsonify({'error': 'Invalid Instagram URL'}), 400

    try:
        # Clean up old downloads
        cleanup_downloads()

        # Load the post
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        # Check if the post contains a video
        if post.is_video:
            # Download the post to the downloads directory
            L.download_post(post, target=DOWNLOAD_DIR)
            
            # Find the downloaded video file
            for file in os.listdir(DOWNLOAD_DIR):
                if file.endswith('.mp4'):
                    video_path = os.path.join(DOWNLOAD_DIR, file)
                    return jsonify({
                        'download_url': f'/get_video/{file}',
                        'filename': file
                    })

            return jsonify({'error': 'No video found in the post'}), 400
        else:
            return jsonify({'error': 'The provided post does not contain a video'}), 400

    except instaloader.exceptions.InstaloaderException as e:
        return jsonify({'error': f'Instaloader error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/get_video/<filename>')
def get_video(filename):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
