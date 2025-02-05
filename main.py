from importlib.metadata import version as version_C, PackageNotFoundError
import logging
import subprocess
import sys
logger = logging.getLogger("ContainerMannager")
import requests
import os
import urllib.request
import configparser
import zipfile
import shutil
import xml.etree.ElementTree as ET
import multienv

data = "./data/"
container = "./container/"
work = os.path.abspath("./work/")
temp = "./temp/"
for i in ["TMPDIR", "TEMP", "TMP"]:
    os.environ[i] = os.path.abspath(temp)

if not os.path.isdir(container):
    os.mkdir(container)
if not os.path.isdir(temp):
    os.mkdir(temp)
if not os.path.isdir(data):
    os.mkdir(data)
if not os.path.isdir(work):
    os.mkdir(work)
config_section_repo = "repo"

config = configparser.ConfigParser()
config_file_path = os.path.join(data, "config.ini")
if os.path.exists(config_file_path):
    config.read(config_file_path)
else:
    config.add_section(config_section_repo)
    config.set(config_section_repo, "update", "true")

def vget(category : str, name : str):
    if config.has_option(category, name):
        return config.get(category, name)
    return None

def run():
    root = ET.fromstring(open(os.path.join(container, "aplication.xml"), encoding="utf-8").read())
    env : multienv.EnvMannager = multienv.EnvMannager()
    env += multienv.IniEnvProvider(os.path.join(".venv", "env.ini"))

    modules = []
    for module in root.findall('module'):
        name = module.get('name')
        version = module.get('version')
        modules.append({'name': name, 'version': version})

    modules_install = []
    for module in modules:
        try:
            if not (version_C(module["name"]) == module["version"]):
                modules_install.append(module)
        except PackageNotFoundError:
            modules_install.append(module)
            logger.warning(f"{module['name']} is not installed.")

    pip_flags = str(root.find('pip').get('flags')).split(" ")

    for module in modules_install:
        subprocess.check_call([sys.executable, "-m", "pip", *pip_flags, "install", f"{module['name']}=={module['version']}"])


    run = root.find('run')
    run_info = {
        'file': run.get('file')
    }

    sys.path.append(os.path.abspath(container))
    os.chdir(container)

    for module in root.findall('env'):
        env += (module.get('path'), module.get('type'))

    env.load()
    env.setGlobal()
    os.work_dir = work

    with open(run_info["file"], "r", encoding="utf-8") as f:
        script_code = f.read()
    exec(script_code, {"__name__": "__main__", "__file__": "main.py"})

repo_url = "https://api.github.com/repos/{owner}/{repo}/releases/latest"
repo_url = repo_url.format(owner="flaim4", repo="DeltaBotDiscord")
try:
    if vget(config_section_repo, "update") == "true":
        response = requests.get(repo_url)

        if response.status_code == 200:
            release_data = response.json()
            if not (vget(config_section_repo, "version") == release_data.get('tag_name')):
                code_temp_file = os.path.join(temp, "code.temp")
                urllib.request.urlretrieve(
                    "https://github.com/{owner}/{repo}/archive/refs/tags/{tag}.zip".format(owner="flaim4",
                                                                                           repo="DeltaBotDiscord",
                                                                                           tag=release_data.get(
                                                                                               'tag_name')),
                    code_temp_file)
                with zipfile.ZipFile(code_temp_file, 'r') as zip_ref:
                    first_folder = zip_ref.namelist()[0].split('/')[0]
                    zip_ref.extractall(temp)
                source_dir = os.path.join(temp, first_folder)
                if os.path.exists(container):
                    shutil.rmtree(container)
                shutil.copytree(source_dir, container)
                shutil.rmtree(source_dir)
                os.remove(code_temp_file)
                config.set(config_section_repo, "version", release_data.get('tag_name'))
                with open(config_file_path, 'w') as configfile:
                    config.write(configfile)
        else:
            raise RuntimeError()
except:
    logger.warning("Не удалось получить информацию о релизах.")

run()

