#!/usr/bin/env python3
"""Copy this skill into a chosen runtime's skill directory, without overwriting an installation."""
import argparse
from pathlib import Path
import shutil

NAME='cftc-agricultural-positioning'

def install(destination):
    source=Path(__file__).resolve().parent.parent
    target=destination.expanduser().resolve()/NAME
    if target.exists():raise FileExistsError('Installation already exists: '+str(target))
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(source,target,ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc','.venv'))
    return target

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skills-dir',required=True,type=Path,help='The runtime skill-directory path, without the skill name.')
    args=parser.parse_args()
    print(install(args.skills_dir))

if __name__=='__main__':main()
