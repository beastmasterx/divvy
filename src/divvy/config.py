"""
Configuration utilities for loading environment variables from .env files.
Supports environment-specific configuration files.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    # dotenv is optional - provide a no-op function if not installed
    def load_dotenv(*args, **kwargs):
        pass


def load_env_files(project_root: Path | None = None, verbose: bool = False) -> None:
    """
    Load environment variables from .env files.
    
    Supports environment-specific files like .env.dev, .env.production, etc.
    Set DIVVY_ENV or ENV environment variable to specify the environment.
    Example: DIVVY_ENV=dev will load .env.dev
    
    Priority order (later files override earlier ones):
    1. Base .env file from project root
    2. Base .env file from current working directory (if different)
    3. Environment-specific .env.{ENV} file from project root
    4. Environment-specific .env.{ENV} file from current working directory (if different)
    5. Shell environment variables (always highest priority)
    
    Args:
        project_root: Path to project root directory. If None, auto-detects from
                     the location of this file (3 levels up from src/divvy/config.py).
        verbose: If True, prints which .env files are being loaded.
    """
    if project_root is None:
        # Auto-detect project root (3 levels up from src/divvy/config.py)
        project_root = Path(__file__).parent.parent.parent
    
    cwd = Path.cwd()
    
    # Determine environment from environment variable
    env_name = os.getenv("DIVVY_ENV") or os.getenv("ENV") or os.getenv("ENVIRONMENT")
    
    # Load base .env file first (lower priority)
    env_files_to_load = []
    
    # Base .env file from project root
    base_env = project_root / ".env"
    if base_env.exists():
        env_files_to_load.append(base_env)
        if verbose:
            print(f"Loading base config: {base_env.relative_to(project_root)}")
    
    # Base .env file from current working directory
    cwd_base_env = cwd / ".env"
    if cwd_base_env.exists() and cwd_base_env != base_env:
        env_files_to_load.append(cwd_base_env)
        if verbose:
            print(f"Loading base config from CWD: {cwd_base_env}")
    
    # Load environment-specific .env file (higher priority, overrides base)
    if env_name:
        env_specific = project_root / f".env.{env_name}"
        if env_specific.exists():
            env_files_to_load.append(env_specific)
            if verbose:
                print(f"Loading environment-specific config: .env.{env_name}")
        
        cwd_env_specific = cwd / f".env.{env_name}"
        if cwd_env_specific.exists() and cwd_env_specific != env_specific:
            env_files_to_load.append(cwd_env_specific)
            if verbose and cwd_env_specific != project_root / f".env.{env_name}":
                print(f"Loading environment-specific config from CWD: .env.{env_name}")
    
    # Load all .env files in order (later files override earlier ones)
    # override=False ensures shell env vars always take precedence
    for env_file in env_files_to_load:
        load_dotenv(env_file, override=False)

