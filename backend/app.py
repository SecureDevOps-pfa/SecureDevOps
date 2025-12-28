from flask import Flask, request, jsonify
from services.upload_service import handle_zip_upload

app = Flask(__name__)

@app.route("/api/jobs", methods=["POST"])
def create_job():
    if "project_zip" not in request.files:
        return jsonify({"error": "Missing project_zip field"}), 400

    file = request.files["project_zip"]

    if not file.filename.lower().endswith(".zip"):
        return jsonify({"error": "Only ZIP files are allowed"}), 400

    try:
        metadata = handle_zip_upload(file)
        return jsonify(metadata), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(debug=True)
