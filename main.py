from flask import Flask, render_template_string, request, send_file, send_from_directory
import yt_dlp
import os

app = Flask(__name__)

# Dossier temporaire pour stocker les téléchargements sur Render
DOWNLOAD_FOLDER = '/tmp'

# HTML de la page d'accueil (Interface utilisateur)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Markus Téléchargeur</title>
    
    <link rel="icon" type="image/png" href="/icon.png">
    
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f7f6;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            text-align: center;
            max-width: 400px;
            width: 100%;
        }
        h1 { color: #333; margin-bottom: 20px; }
        input[type="text"] {
            width: 90%;
            padding: 10px;
            margin-bottom: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        button {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            width: 95%;
        }
        button:hover { background-color: #0056b3; }
        .footer { margin-top: 20px; font-size: 12px; color: #777; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Markus Téléchargeur</h1>
        <form action="/download" method="post">
            <input type="text" name="url" placeholder="Collez le lien de la vidéo ici" required>
            <button type="submit">Télécharger la vidéo</button>
        </form>
        <div class="footer">Propulsé par Render et yt-dlp</div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

# Cette route permet à Flask de donner ton image icon.png au navigateur pour l'onglet
@app.route('/icon.png')
def favicon():
    return send_from_directory(os.getcwd(), 'icon.png')

@app.route('/download', methods=['POST'])
def download():
    video_url = request.form.get('url')
    if not video_url:
        return "Veuillez fournir un lien valide.", 400

    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            
        return send_file(filename, as_attachment=True)
        
    except Exception as e:
        return f"Une erreur est survenue lors du téléchargement : {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
