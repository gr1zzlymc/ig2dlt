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
        m = re.search(r"instagram\.com\/p\/([^\/]+)/", url)
        if not m:
            error = "Invalid Instagram post URL."
        else:
            shortcode = m.group(1)
            # 1) Try the “?__a=1&__d=dis” JSON endpoint
            json_url = f"https://www.instagram.com/p/{shortcode}/?__a=1&__d=dis"
            try:
                resp = requests.get(
                    json_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                                      "Chrome/122.0.0.0 Safari/537.36"
                    },
                    timeout=10
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # Depending on IG version, the path can be either data["graphql"]["shortcode_media"]
                    # or (older) data["items"][0], but current endpoint uses graphql.
                    media = data.get("graphql", {}).get("shortcode_media", None)
                    if not media:
                        raise Exception("No shortcode_media in JSON response")
                else:
                    raise Exception(f"Endpoint returned {resp.status_code}")

            except Exception:
                # 2) Fallback: fetch the HTML & parse out __NEXT_DATA__
                post_url = f"https://www.instagram.com/p/{shortcode}/"
                try:
                    page = requests.get(
                        post_url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                                          "Chrome/122.0.0.0 Safari/537.36"
                        },
                        timeout=10
                    )
                    if page.status_code != 200:
                        raise Exception(f"Status {page.status_code}")
                    html = page.text

                    # Look for <script id="__NEXT_DATA__">…</script>
                    next_data_match = re.search(
                        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>\s*(\{.*?\})\s*</script>',
                        html,
                        re.DOTALL
                    )
                    if not next_data_match:
                        raise Exception("Could not find __NEXT_DATA__ paragraph")

                    next_data = json.loads(next_data_match.group(1))
                    # Navigate to graphql → shortcode_media
                    media = next_data["props"]["pageProps"]["graphql"]["shortcode_media"]
                except Exception as e:
                    error = f"Failed to load post: {e}"
                    media = None

            # If we have a valid media dict, extract URLs
            if media and not error:
                try:
                    if media.get("__typename") == "GraphSidecar":
                        edges = media["edge_sidecar_to_children"]["edges"]
                        images = [node["node"]["display_url"] for node in edges]
                    else:
                        images = [media["display_url"]]
                except Exception as e:
                    error = f"Failed to parse media JSON: {e}"

    return render_template("index.html", images=images, error=error)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"
