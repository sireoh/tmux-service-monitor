from flask import Flask, request, jsonify, render_template_string
import subprocess

app = Flask(__name__)

# Function to execute shell commands
def run_command(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>tmux Service Manager</title>
        <script>
            async function fetchServices() {
                let response = await fetch('/services');
                let data = await response.json();
                document.getElementById("services").innerHTML = data.services.map(s => `
                    <li>
                        ${s.session}:${s.window_name} (index ${s.window_index})
                        <button onclick="stopService('${s.session}', '${s.window_index}')">Stop</button>
                        <button onclick="checkStatus('${s.session}')">Check Session Status</button>
                    </li>
                `).join('');
            }

            async function fetchSessions() {
                let response = await fetch('/sessions');
                let data = await response.json();
                document.getElementById("session_radios").innerHTML = data.sessions.map((s, i) => `
                    <label>
                        <input type="radio" name="session" value="${s}" ${i === 0 ? 'checked' : ''}> ${s}
                    </label><br>
                `).join('');
            }

            async function startService() {
                let name = document.getElementById("service_name").value;
                let commandRaw = document.getElementById("service_command").value;
                let session = document.querySelector('input[name="session"]:checked')?.value;

                if (!name || !commandRaw || !session) return alert("Fill in all fields!");

                let command = commandRaw.split('\n').map(line => line.trim()).filter(line => line).join(' && ');

                await fetch('/start', { 
                    method: 'POST', 
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, command, session})
                });

                fetchServices();
                fetchSessions();
            }

            async function stopService(session, window) {
                await fetch('/stop', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({session, window})
                });
                fetchServices();
            }

            async function checkStatus(session) {
                let response = await fetch(`/status?name=${session}`);
                let data = await response.json();
                alert(`Session ${session} is ${data.status}`);
            }

            window.onload = () => {
                fetchServices();
                fetchSessions();
            };
        </script>
    </head>
    <body>
        <h1>Tmux Service Manager</h1>

        <h2>Running Services</h2>
        <ul id="services">Loading services...</ul>

        <h2>Start New Service</h2>
        <div>
            <label>Service Name:</label><br>
            <input type="text" id="service_name"><br><br>

            <label>Command:</label><br>
            <textarea id="service_command" rows="4" cols="50"></textarea><br><br>

            <label>Select Session:</label><br>
            <div id="session_radios">Loading sessions...</div>

            <button onclick="startService()">Start</button>
        </div>
    </body>
    </html>
    """)

@app.route('/sessions', methods=['GET'])
def list_sessions():
    output = run_command("tmux list-sessions")
    sessions = [line.split(":")[0] for line in output.split("\n") if line]
    return jsonify({"sessions": sessions})

@app.route('/services', methods=['GET'])
def list_services():
    output = run_command("tmux list-windows -a -F '#S:#I:#W'")
    services = []
    for line in output.split("\n"):
        if line:
            try:
                session, window_index, window_name = line.split(":")
                services.append({
                    "session": session,
                    "window_index": window_index,
                    "window_name": window_name
                })
            except ValueError:
                continue
    return jsonify({"services": services})

@app.route('/start', methods=['POST'])
def start_service():
    data = request.json
    service_name = data.get("name")
    command = data.get("command")
    session = data.get("session")

    if not service_name or not command or not session:
        return jsonify({"error": "Missing fields"}), 400

    # Safely wrap the command
    full_cmd = f'tmux new-window -t {session} -n {service_name} "bash -c \'{command}\'"'
    result = run_command(full_cmd)

    return jsonify({
        "message": f"Started window '{service_name}' in session '{session}'",
        "debug_command": full_cmd,
        "output": result
    }), 200

@app.route('/stop', methods=['POST'])
def stop_service():
    data = request.json
    session = data.get("session")
    window = data.get("window")

    if not session or not window:
        return jsonify({"error": "Missing session or window name"}), 400

    run_command(f"tmux kill-window -t {session}:{window}")
    return jsonify({"message": f"Stopped window '{window}' in session '{session}'"}), 200

@app.route('/status', methods=['GET'])
def service_status():
    session = request.args.get("name")
    output = run_command(f"tmux has-session -t {session} 2>/dev/null && echo 'running' || echo 'stopped'")
    return jsonify({"status": output})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)