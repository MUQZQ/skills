"""按 PR 轮次获取 PR Helper 评审正文与原图。只使用 Python 标准库。"""

import argparse
import hashlib
import json
import os
import re
import sys
from tempfile import TemporaryDirectory
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


PAGE_SIZE = 50
JSON_LIMIT = 12 * 1024 * 1024
PNG_LIMIT = 32 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MARKDOWN_IMAGE = re.compile(r'!\[([^\]\n]*)\]\(\s*(<?[^)\s>]+>?)')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PrHelper:
    def __init__(self, server, app_path, key, interval):
        parsed = urlsplit(server)
        loopback = parsed.hostname in {"127.0.0.1", "::1", "localhost"}
        if (
            not parsed.hostname
            or (parsed.scheme != "https" and not (parsed.scheme == "http" and loopback))
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("服务地址应为 HTTPS 站点根地址，可含端口。")
        if not re.fullmatch(r"/serve/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+", app_path):
            raise ValueError("应用路径应形如 /serve/组织/应用。")
        self.origin = server.rstrip("/")
        self.app_path = app_path
        self.api = app_path + "/api"
        self.headers = {"X-API-Key": key}
        self.interval = interval
        self.last_call = None
        self.opener = build_opener(NoRedirect)

    def read(self, route, limit, payload=None):
        headers = self.headers.copy()
        if payload is not None:
            payload = json.dumps({"params": payload}).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(self.origin + route, data=payload, headers=headers)
        for attempt in range(3):
            if self.last_call is not None:
                time.sleep(max(0, self.interval - (time.monotonic() - self.last_call)))
            self.last_call = time.monotonic()
            try:
                with self.opener.open(request, timeout=30) as response:
                    data = response.read(limit + 1)
                if len(data) > limit:
                    raise ValueError("响应超出大小限制：" + route)
                return data
            except HTTPError as error:
                if error.code in {429, 502, 503, 504} and attempt < 2:
                    error.close()
                    time.sleep(max(1, self.interval) * (attempt + 1))
                    continue
                error.close()
                if error.code in {401, 403}:
                    raise ValueError("PR Helper 拒绝访问。请检查服务地址、授权和 PRHELP_API_KEY。") from error
                raise ValueError(f"PR Helper 返回 HTTP {error.code}，路径 {route}。") from error
        raise RuntimeError("PR Helper 请求未完成。")

    def query(self, name, params):
        reply = json.loads(self.read(self.api + "/queries/" + name, JSON_LIMIT, params))
        data = reply.get("data") if isinstance(reply, dict) else None
        rows = data.get("rows") if isinstance(data, dict) else None
        if not isinstance(reply, dict) or reply.get("success") is False or not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
            raise ValueError("PR Helper 查询返回了意外结构：" + name)
        return rows

    def reviews(self, pr):
        all_rows = {}
        offset = 0
        for _ in range(100):
            page = self.query("$pr_reviews.byPr", {"prNumber": pr, "limit": PAGE_SIZE, "offset": offset})
            before = len(all_rows)
            for row in page:
                try:
                    row_id = int(row["id"])
                except (KeyError, TypeError, ValueError) as error:
                    raise ValueError("轮次列表存在无效的评审 ID。") from error
                all_rows[row_id] = row
            if len(page) < PAGE_SIZE:
                return [all_rows[r] for r in sorted(all_rows, reverse=True)]
            if len(all_rows) == before:
                raise ValueError("评审分页未推进，请核对服务查询契约。")
            offset += len(page)
        raise ValueError("评审列表超出单次收集上限。")

    def screenshots(self, body):
        allowed = self.api + "/content/"
        origin = urlsplit(self.origin)
        for match in MARKDOWN_IMAGE.finditer(body):
            label, reference = match[1], match[2].strip("<>")
            parsed = urlsplit(reference)
            if parsed.netloc and (parsed.scheme, parsed.netloc) != (origin.scheme, origin.netloc):
                continue
            if parsed.query or parsed.fragment or not parsed.path.startswith(allowed):
                continue
            name = parsed.path[len(allowed):]
            if re.fullmatch(r"[0-9a-fA-F]{8,128}\.png", name):
                yield label, parsed.path, name

    def review_url(self, pr):
        origin = urlsplit(self.origin)
        return urlunsplit((origin.scheme, origin.netloc, self.app_path.removeprefix("/serve") + "/", "", f"/pr/{pr}"))

    def collect(self, pr, round_id, output, with_images):
        review = next((row for row in self.reviews(pr) if int(row["id"]) == round_id), None)
        if review is None:
            raise ValueError(f"在 PR #{pr} 的轮次列表中找不到评审 {round_id}。")
        rows = self.query("$pr_reviews.bodyById", {"id": round_id})
        body = rows[0].get("body_md") if len(rows) == 1 else None
        if not isinstance(body, str) or not body.strip():
            raise ValueError(f"评审 {round_id} 未返回正文。")
        destination = output / f"pr-{pr}-round-{round_id}"
        output.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(destination)
        with TemporaryDirectory(prefix=".prhelp-", dir=output) as work:
            stage = Path(work) / "evidence"
            stage.mkdir()
            (stage / "review.md").write_text(body, encoding="utf-8")
            review_file = stage / "manifest.json"
            manifest = {
                "pr": pr,
                "review_id": round_id,
                "review_url": self.review_url(pr),
                "head_sha": review.get("head_sha"),
                "reviewed_at": review.get("reviewed_at"),
                "verdict": review.get("verdict"),
                "verification": review.get("verification"),
                "screenshots": [],
            }

            captured = {}
            for label, route, name in self.screenshots(body):
                item = {"label": label, "source_url": self.origin + route}
                if with_images:
                    if name not in captured:
                        data = self.read(route, PNG_LIMIT)
                        if not data.startswith(PNG_SIGNATURE):
                            raise ValueError("原图接口未返回 PNG：" + name)
                        relative = "images/" + name
                        file = stage / relative
                        file.parent.mkdir(exist_ok=True)
                        file.write_bytes(data)
                        captured[name] = (relative, hashlib.sha256(data).hexdigest())
                    item["file"], item["sha256"] = captured[name]
                manifest["screenshots"].append(item)
            review_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if destination.exists():
                raise FileExistsError(destination)
            stage.rename(destination)
        return destination


def positive(value):
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("请输入正整数。")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default=os.getenv("PRHELP_SERVER"), help="服务根地址，或设置 PRHELP_SERVER")
    parser.add_argument("--app-path", default="/serve/patodo/pr-help", help="PR Helper 服务路径")
    parser.add_argument("--interval", type=float, default=3.0, help="同服务请求的最短间隔，单位秒")
    actions = parser.add_subparsers(dest="command", required=True)
    listing = actions.add_parser("reviews", help="列出指定 PR 的评审轮次")
    listing.add_argument("--pr", type=positive, required=True)
    collect = actions.add_parser("collect", help="获取指定轮次的实际证据")
    collect.add_argument("--pr", type=positive, required=True)
    collect.add_argument("--round", type=positive, required=True)
    collect.add_argument("--out", type=Path, required=True)
    collect.add_argument("--images", action="store_true", help="下载评审引用的同源 PNG 原图")
    args = parser.parse_args()

    secret = os.getenv("PRHELP_API_KEY", "").strip()
    if not args.server or not secret:
        parser.error("提供 --server 或 PRHELP_SERVER，并通过环境变量提供 PRHELP_API_KEY。")
    if not 0 <= args.interval <= 60:
        parser.error("--interval 需在 0 到 60 秒之间。")
    try:
        client = PrHelper(args.server, args.app_path, secret, args.interval)
        if args.command == "reviews":
            allowed = ("id", "head_sha", "reviewed_at", "verdict", "verification", "summary")
            print(json.dumps([{k: row.get(k) for k in allowed} for row in client.reviews(args.pr)],
                             ensure_ascii=False, indent=2))
        else:
            print(client.collect(args.pr, args.round, args.out, args.images))
    except FileExistsError:
        parser.exit(2, "取证目录已存在。请选择新的输出目录，保留已有取证。\n")
    except (OSError, ValueError, URLError) as error:
        parser.exit(2, f"取证未完成：{error}\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
