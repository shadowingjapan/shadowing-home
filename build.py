#!/usr/bin/env python3
"""
쉐도잉 일본어 홈페이지 자동 빌드 스크립트
YouTube Data API v3로 채널의 재생목록/영상 데이터를 수집해 index.html을 재생성합니다.

필요 환경변수:
  YT_API_KEY : YouTube Data API v3 키 (GitHub Actions에서는 Secrets로 주입)
"""
import json, os, re, sys, urllib.request, urllib.parse
from datetime import datetime, timezone

CHANNEL_ID = "UCjljs0dZ3Z2tkwBWOfCwjvQ"
UPLOADS_PL = "UUjljs0dZ3Z2tkwBWOfCwjvQ"   # 채널 전체 업로드 재생목록
API = "https://www.googleapis.com/youtube/v3/"
KEY = os.environ.get("YT_API_KEY", "").strip()

if not KEY:
    sys.exit("오류: 환경변수 YT_API_KEY가 없습니다. GitHub Secrets에 API 키를 등록하세요.")


def api(endpoint, **params):
    params["key"] = KEY
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def paged(endpoint, **params):
    items, token = [], None
    while True:
        p = dict(params, maxResults=50)
        if token:
            p["pageToken"] = token
        data = api(endpoint, **p)
        items += data.get("items", [])
        token = data.get("nextPageToken")
        if not token:
            return items


# ---------- 표기 포맷 ----------
def fmt_views(n):
    n = int(n)
    if n >= 100_000_000:
        v = n / 100_000_000
        s = f"{v:.0f}" if v >= 10 else f"{v:.1f}".rstrip("0").rstrip(".")
        return s + "억회"
    if n >= 10_000:
        v = n / 10_000
        s = f"{v:.0f}" if v >= 10 else f"{v:.1f}".rstrip("0").rstrip(".")
        return s + "만회"
    return f"{n:,}회"


def fmt_subs(n):
    n = int(n)
    if n >= 10_000:
        v = n / 10_000
        return f"{v:.1f}".rstrip("0").rstrip(".") + "만"   # 천 단위까지 표기 (예: 11.3만)
    return f"{n:,}"


def fmt_ago(iso):
    then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    days = (datetime.now(timezone.utc) - then).days
    if days < 1:   return "오늘"
    if days < 7:   return f"{days}일 전"
    if days < 31:  return f"{days // 7}주 전"
    if days < 365: return f"{days // 30}개월 전"
    return f"{days // 365}년 전"


# ---------- 수집 ----------
def collect():
    print("0/4 채널 정보(구독자 수) 수집...")
    ch = api("channels", part="statistics", id=CHANNEL_ID)
    subs = ch["items"][0]["statistics"].get("subscriberCount")

    print("1/4 재생목록 목록 수집...")
    pls = paged("playlists", part="snippet,contentDetails", channelId=CHANNEL_ID)
    playlists = [{"id": p["id"], "title": p["snippet"]["title"],
                  "count": p["contentDetails"]["itemCount"]} for p in pls]
    print(f"   재생목록 {len(playlists)}개")

    print("2/4 전체 업로드 영상 수집...")
    ups = paged("playlistItems", part="snippet,contentDetails", playlistId=UPLOADS_PL)
    videos = {}
    for it in ups:
        vid = it["contentDetails"]["videoId"]
        sn = it["snippet"]
        if sn.get("title") in ("Private video", "Deleted video"):
            continue
        videos[vid] = {"v": vid, "t": sn["title"],
                       "pub": it["contentDetails"].get("videoPublishedAt") or sn["publishedAt"]}
    print(f"   영상 {len(videos)}개")

    print("3/4 조회수 수집...")
    ids = list(videos.keys())
    for i in range(0, len(ids), 50):
        batch = api("videos", part="statistics", id=",".join(ids[i:i + 50]))
        for v in batch.get("items", []):
            vc = v.get("statistics", {}).get("viewCount")
            if vc is not None:
                videos[v["id"]]["views"] = int(vc)

    print("4/4 재생목록별 영상 순서 수집...")
    pl_vids = {}
    for p in playlists:
        try:
            its = paged("playlistItems", part="contentDetails,snippet", playlistId=p["id"])
            pl_vids[p["id"]] = [
                {"v": x["contentDetails"]["videoId"], "t": x["snippet"]["title"],
                 "pub": x["contentDetails"].get("videoPublishedAt") or x["snippet"]["publishedAt"]}
                for x in its
                if x["snippet"].get("title") not in ("Private video", "Deleted video")]
        except Exception as e:
            print(f"   경고: {p['title']} 수집 실패 — {e}")
            pl_vids[p["id"]] = []
    print("추가: 회원 전용 영상 목록 수집...")
    members = []
    try:
        mo = paged("playlistItems", part="contentDetails",
                   playlistId="UUMO" + CHANNEL_ID[2:])
        members = [x["contentDetails"]["videoId"] for x in mo]
        print(f"   회원 전용 {len(members)}개")
    except Exception as e:
        print(f"   회원 전용 목록 수집 불가(건너뜀) — {e}")
    return playlists, videos, pl_vids, subs, members


# ---------- 신규 재생목록 자동 분류 ----------
def auto_classify(title):
    m = re.search(r"N([1-5])", title)
    if m and re.search(r"JLPT|능력시험", title):
        level = "N" + m.group(1)
        if re.search(r"문법|문형", title): ty = "grammar"
        elif "한자" in title:              ty = "kanji"
        elif "문장" in title:              ty = "sentence"
        else:                              ty = "vocab"
        lv = {"N5": "초급", "N4": "초중급", "N3": "중급", "N2": "중고급", "N1": "고급"}[level]
        return {"group": "jlpt", "level": level, "type": ty, "lv": lv,
                "st": "연재중", "pdf": False, "rec": False, "new": True, "order": 999}
    if re.search(r"한자", title):
        return {"group": "inter", "sub": "한자", "lv": "중급", "st": "연재중",
                "pdf": False, "rec": False, "new": True, "order": 999}
    if re.search(r"관용|사자성어|오노마토페|속담", title):
        return {"group": "inter", "sub": "표현 · 관용어", "lv": "중급", "st": "연재중",
                "pdf": False, "rec": False, "new": True, "order": 999}
    if re.search(r"뉴스|취업|직장", title):
        return {"group": "inter", "sub": "실전 어휘", "lv": "중급", "st": "연재중",
                "pdf": False, "rec": False, "new": True, "order": 999}
    if re.search(r"여행|회화|명대사", title):
        return {"group": "basic", "sub": "여행 · 회화", "lv": "초급", "st": "연재중",
                "pdf": False, "rec": False, "new": True, "order": 999}
    if re.search(r"활용|동사|형용사|문법", title):
        return {"group": "basic", "sub": "문법 · 활용", "lv": "초중급", "st": "연재중",
                "pdf": False, "rec": False, "new": True, "order": 999}
    if re.search(r"문장", title):
        return {"group": "basic", "sub": "문장 연습", "lv": "초중급", "st": "연재중",
                "pdf": False, "rec": False, "new": True, "order": 999}
    return {"group": "basic", "sub": "기본 단어", "lv": "초급", "st": "연재중",
            "pdf": False, "rec": False, "new": True, "order": 999}


# ---------- 조립 ----------
def build_site_data(playlists, videos, pl_vids, curation, subs=None):
    meta = curation["meta"]
    title_of = {p["id"]: p["title"] for p in playlists}
    now = datetime.now(timezone.utc)

    def clean(v):
        full = videos.get(v["v"], v)
        views = full.get("views")
        pub = full.get("pub", v.get("pub", "2020-01-01T00:00:00Z"))
        days = (now - datetime.fromisoformat(pub.replace("Z", "+00:00"))).days
        return {"v": v["v"], "t": full.get("t", v.get("t", "")),
                "w": fmt_views(views) if views is not None else "",
                "d": fmt_ago(pub),
                "vn": views if views is not None else 0,
                "dd": days}

    uploads = sorted(videos.values(), key=lambda x: x["pub"], reverse=True)
    uploads = [clean(v) for v in uploads]

    def entry(pid, m):
        return {"id": pid, "name": title_of.get(pid, ""), "lv": m.get("lv", ""),
                "st": m.get("st", ""), "pdf": m.get("pdf", False),
                "rec": m.get("rec", False), "new": m.get("new", False),
                "sub": m.get("sub", ""),
                "level": m.get("level"), "type": m.get("type"),
                "vids": [clean(v) for v in pl_vids.get(pid, [])]}

    groups_def = [
        ("basic", "기초부터 중급까지", "일본어를 시작하는 분들과 중급을 목표로 하는 분들을 위한 코스"),
        ("inter", "중급 이상 학습자", "한자, 관용표현, 실전 어휘까지 — 깊이를 더하는 코스"),
    ]
    buckets = {"basic": [], "inter": [], "jlpt": []}
    for p in playlists:
        m = meta.get(p["id"]) or auto_classify(p["title"])
        if not pl_vids.get(p["id"]):
            continue  # 비어있는 재생목록 제외
        buckets[m.get("group", "basic")].append((m.get("order", 999), entry(p["id"], m)))

    groups = []
    for key, title, desc in groups_def:
        # 순서 정렬 후, 같은 소그룹(sub)끼리 인접하도록 안정 정렬
        items = [e for _, e in sorted(buckets[key], key=lambda x: x[0])]
        sub_first = {}
        for i, e in enumerate(items):
            sub_first.setdefault(e.get("sub", ""), i)
        items.sort(key=lambda e: (sub_first[e.get("sub", "")],))
        groups.append({"key": key, "title": title, "desc": desc, "items": items})
    jlpt = [e for _, e in sorted(buckets["jlpt"], key=lambda x: x[0])]
    for e in jlpt:
        e["level"] = e.get("level") or "ALL"
        e["type"] = e.get("type") or "vocab"

    return {"uploads": uploads, "groups": groups, "jlptFlat": jlpt,
            "channel": {"name": "쉐도잉 일본어 [SHADOWING日本語]",
                        "handle": "@shadowingjapan",
                        "url": "https://www.youtube.com/@shadowingjapan",
                        "subs": fmt_subs(subs) if subs else ""},
            "asOf": datetime.now(timezone.utc).strftime("%Y-%m-%d")}


def main():
    curation = json.load(open("curation.json", encoding="utf-8"))
    playlists, videos, pl_vids, subs, members = collect()
    data = build_site_data(playlists, videos, pl_vids, curation, subs)
    data["members"] = members

    tpl = open("template.html", encoding="utf-8").read()
    html = tpl.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False))
    html = re.sub(r"\d{4}-\d{2}-\d{2} 수집 기준", data["asOf"] + " 수집 기준", html)
    open("index.html", "w", encoding="utf-8").write(html)
    json.dump(data, open("data.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(f"완료: index.html 생성 — 영상 {len(data['uploads'])}편, "
          f"재생목록 {sum(len(g['items']) for g in data['groups']) + len(data['jlptFlat'])}개, "
          f"구독자 {data['channel']['subs']}")


if __name__ == "__main__":
    main()
