import logging
import uuid
import asyncio
import json
import os
import random
import numpy as np
from pathlib import Path
from .task_base import Task
from libAgents.agents import FuzzerAnalysisAgent, ImprovedFuzzerAgent
from libAgents.utils import Project
from libAgents.config import get_model
from libAgents.model import generate_text
from typing import Optional, Dict, Tuple, Any

logger = logging.getLogger(__name__)

async def deep_evolve_async(
        project_name: str, 
        project_path: str, 
        repo_path: str, 
        harness_id: str, 
        script_content: str, 
        model: str):
    project_bundle = Project(project_path=project_path, repo_path=repo_path, project_name=project_name)
    analyzer = FuzzerAnalysisAgent(
            model=model,
            project_bundle=project_bundle,
            script_content=script_content,
            harness_id=harness_id,
            timeout=1000,
        )

    analysis_report = await analyzer.run()

    if analysis_report is None:
        logger.error("Analysis report is None")
        return None

    improver = ImprovedFuzzerAgent(
            model=model,
            project_bundle=project_bundle,
            analysis_report=analysis_report,
            harness_id=harness_id,
            timeout=1000,
    )

    improved_script = await improver.run()

    if improved_script is None:
        logger.error("Improved script is None")
        return None

    return improved_script


def deep_evolve_sync(
        project_name: str, 
        project_path: str, 
        repo_path: str, 
        harness_id: str, 
        script_content: str, 
        model: str):
    return asyncio.run(deep_evolve_async(project_name, project_path, repo_path, harness_id, script_content, model))

class ScriptSelector:
    def __init__(self, summary_path: str):
        self.summary_path = Path(summary_path)
        self.used_scripts = {}  # script_id -> pick_count
        self._last_mtime = None

    def _load_summary(self) -> Optional[Dict[str, Any]]:
        """Load summary.json file with error handling."""
        if not self.summary_path.exists():
            logger.warning(f"Summary file not found: {self.summary_path}")
            return None
        
        try:
            # Check if file has been modified since last load
            current_mtime = os.path.getmtime(self.summary_path)
            
            # Read the file content
            with open(self.summary_path, 'r') as f:
                content = f.read()
            
            # Try to parse JSON
            try:
                summary_data = json.loads(content)
                self._last_mtime = current_mtime
                return summary_data
            except json.JSONDecodeError as e:
                # File might be in an inconsistent state due to concurrent write
                logger.warning(f"Failed to parse summary.json: {e}. File might be in inconsistent state.")
                return None
                
        except Exception as e:
            logger.error(f"Error loading summary file: {e}")
            return None

    def pick_next_script(self):
        """
        Randomly pick a script from summary.json with preference for less-used scripts and lower error rates.
        
        Returns:
            Optional[Tuple[str, str, str]]: Tuple of (label, harness_name, script_content) or None if no scripts available
        """
        summary_data = self._load_summary()
        if not summary_data:
            return None, None, None
        
        script_scheduler = summary_data.get("script_scheduler", {})
        scripts_stats = summary_data.get("scripts", {})
        if not script_scheduler:
            logger.warning("No scripts found in script_scheduler")
            return None, None, None
        
        # Filter out masked scripts and prepare selection candidates
        candidates = []
        for script_id, scheduler_data in script_scheduler.items():
            if len(scheduler_data) < 3:
                logger.warning(f"Invalid scheduler data for script {script_id}")
                continue
                
            mask_status, sched_cnt, script_info = scheduler_data
            
            # Skip masked scripts
            if mask_status:
                logger.debug(f"Skipping masked script {script_id}")
                continue
            
            # Get error stats for this script
            script_stat = scripts_stats.get(script_id, {})
            summary_stat = script_stat.get("summary", {})
            ttl_errors = summary_stat.get("ttl_errors", 0)
            ttl_execs = summary_stat.get("ttl_execs", 1)  # Avoid division by zero
            
            candidates.append((script_id, script_info, ttl_errors, ttl_execs))
        
        if not candidates:
            logger.info("No unmasked scripts available for selection")
            return None, None, None
        
        # Calculate weights based on pick count and error rate
        weights = []
        for script_id, _, ttl_errors, ttl_execs in candidates:
            # Get pick count from our internal tracking (default to 0 if not picked before)
            pick_count = self.used_scripts.get(script_id, 0)
            
            # Calculate error rate (0.0 to 1.0)
            error_rate = ttl_errors / ttl_execs if ttl_execs > 0 else 0.0
            
            # Calculate pick weight: scripts picked less get higher weight
            # Using exponential decay to make distribution wider
            pick_weight = np.exp(-pick_count * 0.5)
            
            # Calculate error weight: scripts with fewer errors get higher weight
            # Using exponential decay on error rate (scaled by 10 to make it more significant)
            error_weight = np.exp(-error_rate * 10.0)
            
            # Combine weights (multiplicative)
            combined_weight = pick_weight * error_weight
            weights.append(combined_weight)
            
            logger.debug(f"Script {script_id}: pick_count={pick_count}, error_rate={error_rate:.3f}, "
                        f"pick_weight={pick_weight:.3f}, error_weight={error_weight:.3f}, "
                        f"combined_weight={combined_weight:.3f}")
        
        # Normalize weights to create probability distribution
        total_weight = sum(weights)
        if total_weight == 0:
            # Fallback to uniform distribution if all weights are 0
            probabilities = [1.0 / len(candidates)] * len(candidates)
        else:
            probabilities = [w / total_weight for w in weights]
        
        # Random selection based on weights
        selected_idx = np.random.choice(len(candidates), p=probabilities)
        selected_script_id, selected_script_info, selected_ttl_errors, selected_ttl_execs = candidates[selected_idx]
        
        # Update our pick count
        self.used_scripts[selected_script_id] = self.used_scripts.get(selected_script_id, 0) + 1
        
        # Extract information from script_info
        label = selected_script_info.get("task_label", f"script-{selected_script_id}")
        harness_name = selected_script_info.get("harness_name", "unknown")
        script_path = selected_script_info.get("file_path")
        
        # Read script content
        script_content = None
        if script_path:
            script_content = self.get_script_content(script_path)
        
        if script_content is None:
            logger.error(f"Failed to read script content for script {selected_script_id}")
            return None, None, None
        
        error_rate = selected_ttl_errors / selected_ttl_execs if selected_ttl_execs > 0 else 0.0
        logger.info(f"Selected script {selected_script_id} (picked {self.used_scripts[selected_script_id]} times, "
                   f"error rate: {error_rate:.3f}, errors: {selected_ttl_errors}/{selected_ttl_execs})")
        logger.debug(f"Current pick distribution: {self.used_scripts}")
        
        return label, harness_name, script_content
    
    def get_script_content(self, script_path: str) -> Optional[str]:
        """Read the content of a script file."""
        try:
            script_file = Path(script_path)
            if not script_file.exists():
                logger.error(f"Script file not found: {script_path}")
                return None
            
            with open(script_file, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading script file {script_path}: {e}")
            return None
    
    def get_pick_statistics(self) -> Dict[str, int]:
        """Get the current pick count statistics."""
        return self.used_scripts.copy()
    
    def reset_pick_counts(self):
        """Reset all pick counts to start fresh."""
        self.used_scripts.clear()
        logger.info("Reset all script pick counts")
    
    def get_all_scripts(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all scripts with their information from summary.json.
        
        Returns:
            Dict mapping script_id to script information including schedule count
        """
        summary_data = self._load_summary()
        if not summary_data:
            return {}
        
        script_scheduler = summary_data.get("script_scheduler", {})
        scripts = summary_data.get("scripts", {})
        
        result = {}
        for script_id, scheduler_data in script_scheduler.items():
            if len(scheduler_data) < 3:
                continue
                
            mask_status, sched_cnt, script_info = scheduler_data
            
            # Combine scheduler info with script stats and our pick count
            combined_info = {
                "script_id": script_id,
                "mask_status": mask_status,
                "sched_cnt": sched_cnt,
                "script_info": script_info,
                "stats": scripts.get(script_id, {}),
                "selector_pick_count": self.used_scripts.get(script_id, 0)
            }
            result[script_id] = combined_info
        
        return result