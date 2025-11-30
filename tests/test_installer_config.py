import os
import subprocess
import textwrap


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
    assert proc.returncode == 0, f"Installer failed: {proc.stderr}"
    secrets_path = os.path.join("./tests_tmp_install", ".install_secrets")
    assert os.path.exists(secrets_path)
    content = open(secrets_path).read()
    assert "PANEL_DB_USER=env_user" in content
    assert "PANEL_ADMIN_EMAIL=env@example.com" in content


def test_json_config_parsing(tmp_path):
    json_cfg = '{"PANEL_INSTALL_DIR": "./tests_tmp_install_json", "PANEL_DB_USER": "json_user", "PANEL_ADMIN_EMAIL": "json@example.com"}'
    proc, install_dir = run_installer_with_config(tmp_path, json_cfg, "cfg.json")
    assert proc.returncode == 0, f"Installer failed: {proc.stderr}"
    secrets_path = os.path.join("./tests_tmp_install_json", ".install_secrets")
    assert os.path.exists(secrets_path)
    content = open(secrets_path).read()
    assert "PANEL_DB_USER=json_user" in content
    assert "PANEL_ADMIN_EMAIL=json@example.com" in content
