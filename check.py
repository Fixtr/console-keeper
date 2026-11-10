#!/usr/bin/env python3
"""콘솔지기: GCP 프로젝트들의 API 키 제한 상태를 점검하고 한국어 보고서를 출력한다.

사용법:
  python3 check.py              # projects.txt의 프로젝트들을 점검
  python3 check.py --self-test  # gcloud 없이 판정 로직만 검증
종료 코드: 0 = 전부 정상, 1 = 경고 있음, 2 = 실행 오류
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

CLIENT_RESTRICTIONS = (
    "browserKeyRestrictions",
    "androidKeyRestrictions",
    "iosKeyRestrictions",
    "serverKeyRestrictions",
)


def list_keys(project: str) -> list:
    out = subprocess.run(
        ["gcloud", "services", "api-keys", "list",
         "--project", project, "--format", "json"],
        capture_output=True, text=True, timeout=120,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip())
    return json.loads(out.stdout or "[]")


def key_warnings(keys: list) -> list[str]:
    """제한 없는 키들의 경고 메시지 목록을 돌려준다."""
    # shortcut: 클라이언트 제한(리퍼러/패키지/번들/IP) 유무만 본다. API 대상(apiTargets)
    # 제한까지 검사하려면 여기서 restrictions.get("apiTargets")도 확인할 것.
    warns = []
    for k in keys:
        name = k.get("displayName") or k.get("uid", "(이름 없음)")
        r = k.get("restrictions") or {}
        if not any(c in r for c in CLIENT_RESTRICTIONS):
            warns.append(f"'{name}' 키에 클라이언트 제한이 없음")
    return warns


def check_projects(projects: list[str]) -> bool:
    print(f"📋 comPasser 콘솔 점검 ({datetime.now():%Y-%m-%d %H:%M})\n")
    any_warn = False
    for p in projects:
        try:
            keys = list_keys(p)
        except Exception as e:
            any_warn = True
            print(f"⚠️ {p} — 조회 실패: {e}")
            continue
        warns = key_warnings(keys)
        if warns:
            any_warn = True
            print(f"⚠️ {p} — 지금 확인 필요")
            for w in warns:
                print(f"   - {w}")
            print(f"   https://console.cloud.google.com/apis/credentials?project={p}")
        else:
            print(f"✅ {p} — 이상 없음 (키 {len(keys)}개 모두 제한 적용됨)")
    return any_warn


def self_test():
    ok_key = {"displayName": "Android key",
              "restrictions": {"androidKeyRestrictions": {}}}
    bad_key = {"displayName": "Browser key", "restrictions": {}}
    no_restr = {"displayName": "New key"}
    assert key_warnings([ok_key]) == []
    assert len(key_warnings([ok_key, bad_key, no_restr])) == 2
    print("self-test OK")


def main():
    if "--self-test" in sys.argv:
        self_test()
        return 0
    pf = Path(__file__).parent / "projects.txt"
    if not pf.exists():
        print("projects.txt가 없습니다. projects.txt.example을 복사해 "
              "점검할 프로젝트 ID를 한 줄에 하나씩 적으세요.", file=sys.stderr)
        return 2
    projects = [l.strip() for l in pf.read_text().splitlines()
                if l.strip() and not l.startswith("#")]
    return 1 if check_projects(projects) else 0


if __name__ == "__main__":
    sys.exit(main())
