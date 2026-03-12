"""
GitHub Contents API를 통한 파일 자동 커밋 모듈 (github_sync.py)

Streamlit Cloud 환경에서 설정 파일 변경 시 GitHub에 자동 커밋하여
재배포 후에도 변경사항이 유지되도록 합니다.

st.secrets["github"]에 토큰/repo/branch 설정이 없으면 자동 스킵됩니다.
"""
import base64
import json
import logging

import requests

logger = logging.getLogger(__name__)


def _get_github_config():
    """st.secrets에서 GitHub 설정을 읽습니다. 미설정 시 None 반환."""
    try:
        import streamlit as st
        gh = st.secrets.get("github")
        if gh is None:
            return None
        token = gh.get("token")
        repo = gh.get("repo")
        branch = gh.get("branch", "main")
        if not token or not repo:
            return None
        return {"token": token, "repo": repo, "branch": branch}
    except Exception:
        return None


def _get_file_sha(repo, path, branch, headers):
    """기존 파일의 SHA를 조회합니다. 파일이 없으면 None 반환."""
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    params = {"ref": branch}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    if resp.status_code == 200:
        return resp.json().get("sha")
    return None


def commit_file(repo_path, content_bytes, message="auto: update file"):
    """바이너리 파일을 GitHub에 커밋합니다.

    Args:
        repo_path: 저장소 내 상대 경로 (예: "data/target_form/업체.xlsx")
        content_bytes: 파일 내용 (bytes)
        message: 커밋 메시지

    Returns:
        True: 커밋 성공, False: 커밋 실패, None: 설정 미존재(스킵)
    """
    config = _get_github_config()
    if config is None:
        return None

    headers = {
        "Authorization": f"Bearer {config['token']}",
        "Accept": "application/vnd.github.v3+json",
    }

    sha = _get_file_sha(config["repo"], repo_path, config["branch"], headers)

    url = f"https://api.github.com/repos/{config['repo']}/contents/{repo_path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("ascii"),
        "branch": config["branch"],
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(url, headers=headers, json=payload, timeout=30)
    if resp.status_code in (200, 201):
        logger.info(f"GitHub 커밋 성공: {repo_path}")
        return True
    else:
        logger.warning(f"GitHub 커밋 실패 [{resp.status_code}]: {resp.text[:200]}")
        return False


def commit_json(repo_path, data_dict, message="auto: update config"):
    """dict를 JSON으로 직렬화하여 GitHub에 커밋합니다.

    Args:
        repo_path: 저장소 내 상대 경로 (예: "data/users/admin/vendor_config.json")
        data_dict: 저장할 dict
        message: 커밋 메시지

    Returns:
        True: 커밋 성공, False: 커밋 실패, None: 설정 미존재(스킵)
    """
    content = json.dumps(data_dict, ensure_ascii=False, indent=2).encode("utf-8")
    return commit_file(repo_path, content, message)
