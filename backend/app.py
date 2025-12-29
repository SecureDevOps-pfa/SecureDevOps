# backend/app.py
from flask import Flask, request, jsonify

from services.upload_service import handle_zip_upload
from services.github_service import clone_github_repo

app = Flask(__name__)

@app.route("/api/jobs", methods=["POST"])
def create_job():

    # Case 1: ZIP upload
    if "project_zip" in request.files:
        file = request.files["project_zip"]

        if not file.filename.lower().endswith(".zip"):
            return jsonify({"error": "Only ZIP files are allowed"}), 400

        try:
            metadata = handle_zip_upload(file)
            return jsonify(metadata), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    # Case 2: GitHub repo (JSON body)
    if request.is_json:
        data = request.get_json()
        github_url = data.get("github_url")

        if github_url:
            try:
                metadata = clone_github_repo(github_url)
                return jsonify(metadata), 201
            except ValueError as e:
                return jsonify({"error": str(e)}), 400

    return jsonify({
        "error": "Provide either project_zip (file) or github_url (JSON)"
    }), 400

if __name__ == "__main__":
    app.run(debug=True)
