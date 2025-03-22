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
        <title>tmux service monitor</title>
        <script>
            async function fetchServices() {
                let response = await fetch('/services');
                let data = await response.json();
                document.getElementById("services").innerHTML = data.services.map(s => `
                    <li>
                        ${s} 
                        <button onclick="stopService('${s}')">Stop</button>
                        <button onclick="checkStatus('${s}')">Check Status</button>
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
            }
            
            window.onload = () => {
                fetchServices();
                fetchSessions();
            };

        </script>
    </head>
    <body>
        <div>Tmux Service Manager</div>
        <div>Running Services</div>
        <ul id="processes">Loading processes...</ul>
        <div>Start New Process</div>
        <div>
            <div>Process Name:</div>
            <input type="text" id="process_name">
        
            <div>Command:</div>
            <textarea id="service_command" rows="4" cols="50"></textarea>
        
            <div>Select Session:</div>
            <div id="session_radios">Loading sessions...</div>
        
            <div><button onclick="startService()">Start</button></div>
        </div>

    </body>
    </html>
    """)

@app.route('/sessions', methods=['GET'])
def list_sessions():
    output = run_command("tmux list-sessions")
    sessions = [line.split(":")[0] for line in output.split("\n") if line]
    return jsonify({"sessions": sessions})

@app.route('/processes', methods=['GET'])
def list_services():
    output = run_command("tmux list-windows -a")
    processes = []
    for line in output.split("\n"):
        if line:
            try:
                # Get the third colon-separated part, then extract the first word (the window name)
                window_name = line.split(":")[2].split()[0]
                processes.append(window_name)
            except IndexError:
                continue  # skip lines that don't match expected format
    return jsonify({"processes": processes})


@app.route('/start', methods=['POST'])
def start_service():
    service_name = request.json.get("name")
    command = request.json.get("command")
    session = request.json.get("session")

    if not service_name or not command or not session:
        return jsonify({"error": "Missing window name, command, or session"}), 400

    # Create a new window inside the existing session
    run_command(f"tmux new-window -t {session} -n {service_name} '{command}'")
    return jsonify({"message": f"Started window '{service_name}' in session '{session}'"}), 200


@app.route('/stop', methods=['POST'])
def stop_service():
    service_name = request.json.get("name")
    if not service_name:
        return jsonify({"error": "Missing service name"}), 400
    run_command(f"tmux kill-session -t {service_name}")
    return jsonify({"message": f"Stopped {service_name}"}), 200

@app.route('/status', methods=['GET'])
def service_status():
    service_name = request.args.get("name")
    output = run_command(f"tmux has-session -t {service_name} 2>/dev/null && echo 'running' || echo 'stopped'")
    return jsonify({"status": output})



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
