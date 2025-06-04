import os
import re
from flask import Flask, render_template, request

import instaloader
from instaloader import Post

app = Flask(__name__)

# Initialize Instaloader once
L = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_video_thumbnails=False,
    download_comments=False,
    save_metadata=False,
    post_metadata_txt_pattern="",
)

@app.route("/", methods=["GET", "POST"])
def index():
    images = []
    error = None

    if request.method == "POST":
        url = request.form.get("url", "").strip()
        # Basic regex to pull out the shortcode from an Instagram post URL
        m = re.search(r"instagram\.com\/p\/([^\/]+)/", url)
        if not m:
            error = "Invalid Instagram post URL."
        else:
            shortcode = m.group(1)
            try:
                # Fetch Post object via shortcode
                post = Post.from_shortcode(L.context, shortcode)

                # If it's a carousel (multiple images/videos), get all display URLs
                if post.typename == "GraphSidecar":
                    images = [node.display_url for node in post.get_sidecar_nodes()]
                else:
                    # Single‐media post → use post.url
                    images = [post.url]
            except Exception as e:
                error = f"Failed to load: {e}"

    return render_template("index.html", images=images, error=error)

# If running locally with `python app.py`
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
