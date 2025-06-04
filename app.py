import os
import re
import json
from flask import Flask, render_template, request

import requests

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    images = []
    error = None

    if request.method == "POST":
        url = request.form.get("url", "").strip()
        # Extract shortcode from URL
        m = re.search(r"instagram\.com\/p\/([^\/]+)/", url)
        if not m:
            error = "Invalid Instagram post URL."
        else:
            shortcode = m.group(1)
            post_url = f"https://www.instagram.com/p/{shortcode}/"

            try:
                # Fetch the page HTML (pretend to be a browser)
                resp = requests.get(
                    post_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                                      "Chrome/122.0.0.0 Safari/537.36"
                    },
                    timeout=10
                )
                if resp.status_code != 200:
                    raise Exception(f"Status {resp.status_code}")

                html = resp.text

                # Find the `window._sharedData = {...};` blob
                shared_data_match = re.search(
                    r"window\._sharedData = (.*?);\s*</script>",
                    html
                )
                if not shared_data_match:
                    raise Exception("Could not find sharedData in HTML")

                shared_data = json.loads(shared_data_match.group(1))
                media = shared_data["entry_data"]["PostPage"][0]["graphql"]["shortcode_media"]

                # If it's a carousel (multiple images/videos)
                if media.get("__typename") == "GraphSidecar":
                    images = [
                        node["node"]["display_url"]
                        for node in media["edge_sidecar_to_children"]["edges"]
                    ]
                else:
                    # Single‐media post (image/video)
                    images = [media["display_url"]]

            except Exception as e:
                error = f"Failed to load post: {e}"

    return render_template("index.html", images=images, error=error)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
