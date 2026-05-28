import os
import uuid
import threading
import traceback
import yt_dlp
from flask import Flask, request, jsonify, send_file, render_template_string, send_from_directory

app = Flask(__name__)

# Utilisation du dossier /tmp indispensable pour le stockage gratuit sur Render
DOWNLOAD_FOLDER = "/tmp/downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Stockage des tâches
tasks = {}

class DownloadTask:
    def __init__(self, task_id, url, quality, content_type):
        self.task_id = task_id
        self.url = url
        self.quality = quality
        self.content_type = content_type
        self.progress = 0
        self.status = "pending"
        self.error = None
        self.filename = None

def download_worker(task):
    try:
        task.status = "downloading"
        task.progress = 5
        
        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'cookiefile': 'cookies.txt',  # <-- Utilise votre fichier cookies.txt envoyé sur GitHub
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'progress_hooks': [lambda d: update_progress(task, d)],
        }
        
        if task.content_type == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio', 
                'preferredcodec': 'mp3', 
                'preferredquality': '192'
            }]
        else:
            if task.quality == 'best':
                ydl_opts['format'] = 'best'
            elif task.quality == 'standard':
                ydl_opts['format'] = 'best[height<=720]/best'
            else:
                ydl_opts['format'] = 'best[height<=480]/best'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extraction des informations de manière sécurisée
            info = ydl.extract_info(task.url, download=False)
            
            if 'entries' in info:
                if len(info['entries']) > 0:
                    actual_info = info['entries'][0]
                else:
                    raise Exception("Aucun résultat trouvé pour cette recherche.")
            else:
                actual_info = info
                
            # Lancement effectif du téléchargement
            ydl.download([actual_info['webpage_url']])
            filename = ydl.prepare_filename(actual_info)
            
            if task.content_type == 'audio':
                filename = filename.rsplit('.', 1)[0] + '.mp3'
                
            task.filename = os.path.basename(filename)
            
        task.progress = 100
        task.status = "completed"
        
    except Exception as e:
        print("\n--- ERREUR SERVEUR ---")
        traceback.print_exc()
        print("----------------------\n")
        task.error = str(e)
        task.status = "error"

def update_progress(task, d):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate')
        if total and total > 0:
            percent = int(d['downloaded_bytes'] / total * 100)
            if percent > task.progress:
                task.progress = percent
    elif d['status'] == 'finished':
        task.progress = 100

HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Markus Téléchargeur</title>
    <link rel="icon" type="image/png" href="/icon.png">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', system-ui, sans-serif;
            background: radial-gradient(circle at 30% 10%, #0a0518, #000000);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            overflow-x: hidden;
        }
        @keyframes fadeOutSplash {
            0% { opacity: 1; visibility: visible; }
            85% { opacity: 1; visibility: visible; }
            100% { opacity: 0; visibility: hidden; pointer-events: none; }
        }
        .splash {
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.98);
            backdrop-filter: blur(24px);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 2000;
            animation: fadeOutSplash 2.2s forwards;
        }
        .splash h1 {
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(135deg, #ff3366, #ffcc33, #44ff44, #4488ff);
            background-clip: text;
            -webkit-background-clip: text;
            color: transparent;
            text-align: center;
        }
        .gemini-dots {
            display: flex;
            gap: 2rem;
            margin: 2rem 0;
        }
        .gemini-dot {
            font-size: 2.5rem;
            animation: pulse 1.2s infinite;
        }
        @keyframes pulse {
            0% { opacity: 0.3; transform: scale(0.8); }
            50% { opacity: 1; transform: scale(1.2); text-shadow: 0 0 12px currentColor; }
            100% { opacity: 0.3; transform: scale(0.8); }
        }
        .main-container {
            max-width: 1100px;
            width: 90%;
            background: rgba(6,4,20,0.55);
            backdrop-filter: blur(28px);
            border-radius: 2rem;
            padding: 2rem;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 20px 50px rgba(0,0,0,0.5);
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            flex-wrap: wrap;
            gap: 1rem;
        }
        .url-group {
            display: flex;
            gap: 1rem;
            margin: 1rem 0;
        }
        .url-group input {
            flex: 1;
            padding: 1rem;
            border-radius: 3rem;
            border: 1px solid rgba(255,255,255,0.15);
            background: rgba(0,0,0,0.5);
            color: white;
            font-size: 1rem;
            outline: none;
            font-family: inherit;
            transition: 0.2s;
        }
        .url-group input:focus {
            border-color: #4488ff;
            box-shadow: 0 0 0 2px rgba(68,136,255,0.2);
        }
        button {
            background: #3366ff;
            border: none;
            padding: 0.8rem 1.8rem;
            border-radius: 3rem;
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s, transform 0.1s;
            font-family: inherit;
        }
        button:hover { background: #5588ff; }
        button:active { transform: scale(0.98); }
        button:disabled {
            background: #444 !important;
            cursor: not-allowed;
            transform: none !important;
        }
        .options {
            display: flex;
            gap: 2rem;
            margin: 1.8rem 0;
            flex-wrap: wrap;
        }
        .pill {
            background: rgba(0,0,0,0.35);
            backdrop-filter: blur(4px);
            padding: 0.5rem 1.2rem;
            border-radius: 2.5rem;
            border: 1px solid rgba(68,136,255,0.3);
        }
        .pill label {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #aaaac9;
            display: block;
            margin-bottom: 0.2rem;
        }
        select {
            background: transparent;
            border: none;
            color: white;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            outline: none;
            font-family: inherit;
        }
        select option {
            background: #0a0518;
            color: white;
        }
        .promo-area {
            display: none;
            margin-top: 2rem;
            background: rgba(0,0,0,0.5);
            border-radius: 1.5rem;
            padding: 1.5rem;
            text-align: center;
        }
        .progress-bar {
            background: #1e1e2e;
            border-radius: 1rem;
            height: 6px;
            margin: 1rem 0;
            overflow: hidden;
        }
        .progress-fill {
            width: 0%;
            height: 100%;
            background: linear-gradient(90deg, #44ff44, #4488ff);
            transition: width 0.2s;
        }
        .player-container {
            margin-top: 2rem;
            background: #000000cc;
            border-radius: 1rem;
            overflow: hidden;
            display: none;
        }
        video, audio {
            width: 100%;
            max-height: 400px;
            outline: none;
        }
        .status-message {
            margin-top: 1.5rem;
            font-size: 0.95rem;
            color: #aaffaa;
            font-weight: 500;
            text-align: center;
            min-height: 20px;
        }
        .footer {
            margin-top: 2rem;
            text-align: center;
            font-size: 0.75rem;
            color: #8e8eb3;
            border-top: 1px solid rgba(255,255,255,0.05);
            padding-top: 1.5rem;
        }
        .note {
            font-size: 0.7rem;
            color: #9c9cff;
            margin-top: 0.3rem;
        }
        .download-link {
            display: inline-block;
            margin-top: 1rem;
            padding: 0.6rem 1.4rem;
            background: #44ff44;
            color: black;
            border-radius: 2rem;
            text-decoration: none;
            font-weight: bold;
            font-size: 0.85rem;
            transition: transform 0.2s;
        }
        .download-link:hover { transform: scale(1.05); }
    </style>
</head>
<body>

<div id="splash" class="splash">
    <h1>MARKUS TÉLÉCHARGEUR</h1>
    <div class="gemini-dots">
        <span class="gemini-dot" style="color:#ff3366">●</span>
        <span class="gemini-dot" style="color:#ffcc33">●</span>
        <span class="gemini-dot" style="color:#44ff44">●</span>
        <span class="gemini-dot" style="color:#4488ff">●</span>
    </div>
    <p>Initialisation de l'interface...</p>
</div>

<div class="main-container" id="mainContainer">
    <div class="header">
        <h2>MARKUS_H24</h2>
        <span style="background: rgba(255,255,255,0.05); padding: 0.3rem 1rem; border-radius: 2rem; font-size:0.8rem;">✦ ÉDITION ✦</span>
    </div>
    
    <div class="url-group">
        <input type="text" id="query" placeholder="Lien ou titre de la vidéo">
        <button id="pasteBtn">Coller</button>
    </div>
    <div class="note">✍️ Exemple : "himra keou drill" ou https://youtube.com/watch?v=...</div>

    <div class="options">
        <div class="pill">
            <label>QUALITÉ</label>
            <select id="quality">
                <option value="best">Meilleure disponible</option>
                <option value="standard">Standard (720p)</option>
                <option value="normal">Basse (480p)</option>
            </select>
        </div>
        <div class="pill">
            <label>CONTENU</label>
            <select id="content">
                <option value="video">Vidéo (MP4)</option>
                <option value="audio">Musique (MP3)</option>
            </select>
        </div>
    </div>

    <button id="downloadBtn" style="width: 100%; padding: 1.2rem; font-size: 1.1rem; letter-spacing: 1px;">TÉLÉCHARGER</button>

    <div id="promoArea" class="promo-area">
        <h3 style="font-size:1.1rem; margin-bottom: 0.5rem;">TRAITEMENT EN COURS</h3>
        <div class="progress-bar"><div id="progressFill" class="progress-fill"></div></div>
        <p id="progressPercent">0%</p>
    </div>

    <div id="statusDiv" class="status-message"></div>

    <div id="playerContainer" class="player-container"></div>

    <div class="footer">
        <span>Alimenté par yt-dlp</span> — Développé par MARKUS_H24
    </div>
</div>

<script>
    const dots = document.querySelectorAll('.gemini-dot');
    let idx = 0;
    setInterval(() => {
        if(dots.length > 0) {
            dots.forEach(d => d.style.opacity = '0.3');
            if (dots[idx]) dots[idx].style.opacity = '1';
            idx = (idx + 1) % dots.length;
        }
    }, 380);

    document.getElementById('pasteBtn').addEventListener('click', async () => {
        try {
            if (navigator.clipboard && navigator.clipboard.readText) {
                const text = await navigator.clipboard.readText();
                document.getElementById('query').value = text;
            } else {
                alert("Votre navigateur bloque l'accès automatique. Faites Ctrl+V.");
            }
        } catch(e) { 
            alert("Raccourci : Utilisez Ctrl+V directement dans le champ."); 
        }
    });

    const downloadBtn = document.getElementById('downloadBtn');
    const queryInput = document.getElementById('query');
    const qualitySelect = document.getElementById('quality');
    const contentSelect = document.getElementById('content');
    const progressFill = document.getElementById('progressFill');
    const progressPercent = document.getElementById('progressPercent');
    const promoArea = document.getElementById('promoArea');
    const playerContainer = document.getElementById('playerContainer');
    const statusDiv = document.getElementById('statusDiv');

    downloadBtn.addEventListener('click', async () => {
        const query = queryInput.value.trim();
        
        if (!query) {
            statusDiv.style.color = '#ff4444';
            statusDiv.innerText = 'Erreur : Veuillez renseigner un lien ou un mot-clé.';
            return;
        }

        playerContainer.style.display = 'none';
        playerContainer.innerHTML = '';
        promoArea.style.display = 'block';
        progressFill.style.width = '0%';
        progressPercent.innerText = '0%';
        downloadBtn.disabled = true;
        statusDiv.style.color = '#aaffaa';
        statusDiv.innerText = 'Connexion au serveur...';

        const formData = new FormData();
        formData.append('query', query);
        formData.append('quality', qualitySelect.value);
        formData.append('content', contentSelect.value);

        try {
            const res = await fetch('/download', { method: 'POST', body: formData });
            if (!res.ok) throw new Error("Erreur de communication avec le serveur Flask");
            
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            
            const taskId = data.task_id;

            const interval = setInterval(async () => {
                try {
                    const statusRes = await fetch(`/status/${taskId}`);
                    if (!statusRes.ok) return;
                    
                    const statusData = await statusRes.json();
                    const percent = statusData.progress || 0;
                    
                    progressFill.style.width = percent + '%';
                    progressPercent.innerText = percent + '%';
                    statusDiv.innerText = `Téléchargement en cours : ${percent}%`;
                    
                    if (statusData.status === 'completed') {
                        clearInterval(interval);
                        downloadBtn.disabled = false;
                        promoArea.style.display = 'none';
                        
                        const fileUrl = `/download_file/${taskId}`;
                        const isVideo = contentSelect.value === 'video';
                        
                        playerContainer.innerHTML = isVideo
                            ? `<video controls autoplay><source src="${fileUrl}" type="video/mp4"></video>`
                            : `<audio controls autoplay><source src="${fileUrl}" type="audio/mpeg"></audio>`;
                        playerContainer.style.display = 'block';
                        
                        statusDiv.innerHTML = `✨ Prêt !<br><a href="${fileUrl}" class="download-link" download>💾 Sauvegarder sur l'appareil</a>`;
                    }
                    
                    if (statusData.status === 'error') {
                        clearInterval(interval);
                        downloadBtn.disabled = false;
                        promoArea.style.display = 'none';
                        statusDiv.style.color = '#ff4444';
                        statusDiv.innerText = 'Erreur : ' + (statusData.error || 'Impossible de récupérer ce contenu.');
                    }
                } catch (err) {
                    console.error('Erreur boucle statut:', err);
                }
            }, 1000);

        } catch (err) {
            downloadBtn.disabled = false;
            promoArea.style.display = 'none';
            statusDiv.style.color = '#ff4444';
            statusDiv.innerText = 'Erreur : Impossible de joindre le serveur Flask.';
            console.error(err);
        }
    });
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/icon.png')
def favicon():
    return send_from_directory(os.getcwd(), 'icon.png')

@app.route('/download', methods=['POST'])
def download():
    query = request.form.get('query')
    quality = request.form.get('quality', 'best')
    content_type = request.form.get('content', 'video')
    
    if not query:
        return jsonify({'error': 'Donnée manquante'}), 400
        
    if query.startswith(('http://', 'https://', 'www.')):
        url = query
    else:
        url = f"ytsearch1:{query}"
        
    task_id = str(uuid.uuid4())
    task = DownloadTask(task_id, url, quality, content_type)
    tasks[task_id] = task
    
    threading.Thread(target=download_worker, args=(task,), daemon=True).start()
    return jsonify({'task_id': task_id})

@app.route('/status/<task_id>')
def status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Tâche introuvable'}), 404
        
    return jsonify({
        'progress': task.progress,
        'status': task.status,
        'error': task.error,
        'filename': task.filename
    })

@app.route('/download_file/<task_id>')
def download_file(task_id):
    task = tasks.get(task_id)
    if not task or task.status != 'completed' or not task.filename:
        return "Fichier non disponible", 404
        
    path = os.path.join(DOWNLOAD_FOLDER, task.filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name=task.filename)
        
    return "Fichier introuvable sur le disque", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
