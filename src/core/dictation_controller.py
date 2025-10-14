"""
Controller for managing nerd-dictation processes
"""

import subprocess
import os
import signal
from pathlib import Path


class DictationController:
    """Manages nerd-dictation subprocess"""
    
    def __init__(self, config, database):
        self.config = config
        self.database = database
        self.current_process = None
    
    def is_running(self):
        """Check if dictation is currently running"""
        session = self.database.get_current_session()
        if session is None:
            return False
        
        # Check if process is actually running
        try:
            result = subprocess.run(
                ["pgrep", "-f", "nerd-dictation begin"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def start(self, language, model_path):
        """Start dictation with specified model"""
        # Stop any existing session first
        self.stop()
        
        # Path to the venv python
        venv_python = self.config.nerd_dictation_dir / "venv" / "bin" / "python"
        
        # Prepare command - ejecutar con el python del venv
        cmd = [
            str(venv_python),
            str(self.config.nerd_dictation_bin),
            "begin",
            f"--vosk-model-dir={model_path}"
        ]
        
        try:
            # Start the process in background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                cwd=str(self.config.nerd_dictation_dir)
            )
            
            # Wait a bit to check if it started successfully
            import time
            time.sleep(1)
            
            # Check if process is still running
            if process.poll() is not None:
                # Process ended, get error
                stderr = process.stderr.read().decode()
                return False, f"Error al iniciar: {stderr[:200]}"
            
            # Record in database
            model_name = Path(model_path).name
            self.database.start_session(language, model_path, model_name)
            
            return True, f"Dictado iniciado con {model_name}"
        
        except Exception as e:
            return False, f"Error starting dictation: {str(e)}"
    
    def stop(self):
        """Stop current dictation session"""
        try:
            # Path to the venv python
            venv_python = self.config.nerd_dictation_dir / "venv" / "bin" / "python"
            
            # Use nerd-dictation end command with venv python
            result = subprocess.run(
                [str(venv_python), str(self.config.nerd_dictation_bin), "end"],
                capture_output=True,
                timeout=5,
                cwd=str(self.config.nerd_dictation_dir)
            )
            
            # Update database
            self.database.stop_session()
            
            return True, "Dictado detenido"
        
        except subprocess.TimeoutExpired:
            # Force kill if end command hangs
            try:
                subprocess.run(["pkill", "-f", "nerd-dictation begin"])
                self.database.stop_session()
                return True, "Dictado detenido (forzado)"
            except Exception as e:
                return False, f"Error al detener: {str(e)}"
        
        except Exception as e:
            return False, f"Error al detener: {str(e)}"
    
    def restart(self, language, model_path):
        """Restart dictation with new model"""
        self.stop()
        # Small delay to ensure clean stop
        import time
        time.sleep(0.5)
        return self.start(language, model_path)
    
    def get_status(self):
        """Get current dictation status"""
        session = self.database.get_current_session()
        
        if session and self.is_running():
            return {
                "running": True,
                "language": session["language"],
                "model_name": session["model_name"],
                "started_at": session["started_at"]
            }
        else:
            # Clean up stale session if exists
            if session:
                self.database.stop_session()
            
            return {
                "running": False,
                "language": None,
                "model_name": None,
                "started_at": None
            }