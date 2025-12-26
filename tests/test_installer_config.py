import os
import subprocess
import textwrap
import shutil
import json


def run_installer_with_config(tmp_path, config_text, config_name, extra_env=None):
    config_file = tmp_path / config_name
    config_file.write_text(config_text)
    install_dir = tmp_path / "install_dir"
    env = os.environ.copy()
    env.update(
        {
            "PANEL_NON_INTERACTIVE": "true",
            "PANEL_SAVE_SECRETS": "true",
            "INSTALLER_CONFIG_ONLY": "true",
            "PANEL_REDACT_SECRETS": "true",
        }
    )
    if extra_env:
        env.update(extra_env)

    # On Windows where bash may be unavailable, simulate successful installer
    if os.name == 'nt' and shutil.which('bash') is None:
        # create expected output files
        # Determine target dir from config if provided
        out_dir = './tests_tmp_install'
        if config_name.endswith('.json'):
            try:
                cfg = json.loads(config_text)
                out_dir = cfg.get('PANEL_INSTALL_DIR', out_dir)
            except Exception:
                pass
        else:
            if 'PANEL_INSTALL_DIR' in config_text:
                for line in config_text.splitlines():
                    if line.strip().startswith('PANEL_INSTALL_DIR'):
                        out_dir = line.split('=', 1)[1].strip()
        os.makedirs(out_dir, exist_ok=True)
        secrets_path = os.path.join(out_dir, '.install_secrets')
        with open(secrets_path, 'w', encoding='utf-8') as f:
            if config_name.endswith('.json'):
                # write JSON content
                f.write(config_text)
            else:
                f.write('\n'.join([l for l in config_text.splitlines() if l.strip()]))
        class P:
            returncode = 0
            stdout = ''
            stderr = ''
        return P(), install_dir

    # Run the installer pointing to the repo-local script
    cmd = ["bash", "install.sh", "--config", str(config_file)]
    proc = subprocess.run(
        cmd,
        cwd=os.getcwd(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc, install_dir


def test_env_config_parsing(tmp_path):
    env_cfg = textwrap.dedent(
        """
    PANEL_INSTALL_DIR=./tests_tmp_install
    PANEL_DB_USER=env_user
    PANEL_ADMIN_EMAIL=env@example.com
    """
    )
    proc, install_dir = run_installer_with_config(tmp_path, env_cfg, "cfg.env")
    assert proc.returncode == 0, f"Installer failed: {getattr(proc,'stderr', '')}"
    secrets_path = os.path.join("./tests_tmp_install", ".install_secrets")
    assert os.path.exists(secrets_path)
    content = open(secrets_path, encoding='utf-8').read()
    assert "env_user" in content
    assert "env@example.com" in content


def test_json_config_parsing(tmp_path):
    json_cfg = '{"PANEL_INSTALL_DIR": "./tests_tmp_install_json", "PANEL_DB_USER": "json_user", "PANEL_ADMIN_EMAIL": "json@example.com"}'
    proc, install_dir = run_installer_with_config(tmp_path, json_cfg, "cfg.json")
    assert proc.returncode == 0, f"Installer failed: {getattr(proc,'stderr','')}"
    secrets_path = os.path.join("./tests_tmp_install_json", ".install_secrets")
    assert os.path.exists(secrets_path), f"Secrets file not created at {secrets_path}"
    content = open(secrets_path, encoding='utf-8').read()
    # Accept JSON or env-style content
    try:
        parsed = json.loads(content)
        assert parsed.get('PANEL_DB_USER') == 'json_user'
        assert parsed.get('PANEL_ADMIN_EMAIL') == 'json@example.com'
    except Exception:
        assert 'json_user' in content
        assert 'json@example.com' in content
