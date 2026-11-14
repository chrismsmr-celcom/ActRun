# ActRun MCP Server

Serveur MCP qui expose les outils de coordination ActRun à n'importe quel LLM compatible (Claude, GPT, etc.).

## Installation

```bash
cd integrations/mcp-server
pip install -e .

Configuration dans Claude Desktop
Ajoute ceci dans ton fichier de configuration Claude Desktop :
macOS : ~/Library/Application Support/Claude/claude_desktop_config.json
Windows : %APPDATA%\Claude\claude_desktop_config.json

{
  "mcpServers": {
    "actrun": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/chemin/vers/ActRun/integrations/mcp-server/src"
    }
  }
}

Configuration dans Cursor
Dans .cursor/mcp.json :

{
  "mcpServers": {
    "actrun": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/chemin/vers/ActRun/integrations/mcp-server/src"
    }
  }
}

Outils disponibles

Tool
Description
workspace_get_state
Lit l'état actuel du workspace
workspace_create_branch
Crée une branche isolée
workspace_set_in_branch
Modifie une clé dans une branche
workspace_commit
Valide les modifications
lease_acquire
Réserve une ressource
lease_release
Libère une ressource
get_events
Consulte le journal d'événements
Exemple d'utilisation
Demande à Claude :
"Je suis l'agent marketing. Crée une branche, réserve le budget, et mets-le à 15000."
Claude appellera automatiquement :
workspace_create_branch(agent_id="marketing", branch_name="...")
lease_acquire(agent_id="marketing", resource_key="budget")
workspace_set_in_branch(..., key="budget", value=15000)


#### 4. Script de test local
Crée `integrations/mcp-server/test_mcp.py` pour vérifier que le serveur démarre sans erreur :

```python
"""Test rapide pour vérifier que le serveur MCP se lance correctement."""
import subprocess
import sys
import json
import time

def test_server_starts():
    """Vérifie que le serveur démarre et répond à une requête initialize."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="src"
    )
    
    try:
        # Envoyer une requête initialize JSON-RPC
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"}
            }
        }
        
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()
        
        # Lire la réponse (timeout 5s)
        import select
        ready, _, _ = select.select([proc.stdout], [], [], 5.0)
        
        if ready:
            response = proc.stdout.readline()
            print("✅ Le serveur répond !")
            print(f"   Réponse : {response.strip()}")
            return True
        else:
            print("❌ Timeout : le serveur ne répond pas")
            return False
            
    finally:
        proc.terminate()
        proc.wait(timeout=2)


if __name__ == "__main__":
    success = test_server_starts()
    sys.exit(0 if success else 1)

    🛠️ Installation et test

    # 1. Installer le package MCP
cd integrations/mcp-server
pip install -e .

# 2. Vérifier que le serveur démarre
python test_mcp.py

