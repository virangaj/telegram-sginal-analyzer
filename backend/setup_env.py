"""
Create .env file from template
"""

import os
import shutil

env_example = ".env.example"
env_file = ".env"

if not os.path.exists(env_file):
    if os.path.exists(env_example):
        shutil.copy(env_example, env_file)
        print(f"Created {env_file} from template")
        print(f"Please edit {env_file} with your configuration")
    else:
        print(f"Warning: {env_example} not found")
