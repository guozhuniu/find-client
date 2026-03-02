from __future__ import annotations

import argparse
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
import re


def parse_people_from_list_items(html: str) -> list[tuple[str, Optional[str]]]:
    """
    通用规则：从 <li> 文本里拆姓名 + 职位。
    例如：
      - "张三 总经理"
      - "李四 / 渠道负责人"
      - "王五：市场主管"
    返回 [(name, title), ...]，如果无法拆分，则 name=整行、title=None。
    """
    soup = BeautifulSoup(html, "html.parser")
    out: list[tuple[str, Optional[str]]] = []
    for li in soup.find_all("li"):
        text = " ".join(li.get_text(strip=True).split())
        if not text or len(text) < 2:
            continue
        for sep in ["：", ":", "/", "-", "—"]:
            if sep in text:
                parts = [p.strip() for p in text.split(sep, 1)]
                if len(parts) == 2 and parts[0] and parts[1]:
                    out.append((parts[0], parts[1]))
                    break
        else:
            # 没有分隔符就整行当姓名
            out.append((text, None))
    return out


def parse_people_from_pg_leadership(html: str) -> list[tuple[str, Optional[str]]]:
    """
    针对宝洁领导团队页面的定制解析：
    结构模式大致为：
      - 标题（例如 "Jon R. Moeller"）
      - 紧跟一个链接文本，如 "董事会主席 总裁兼首席执行官了解更多"
    我们取标题作为姓名，链接文本去掉“了解更多”后作为职务。
    参考页面：[宝洁领导团队](https://www.pg.com.cn/leadership-team/)
    """
    soup = BeautifulSoup(html, "html.parser")
    out: list[tuple[str, Optional[str]]] = []

    def _is_generic_heading(text: str) -> bool:
        return "一支着眼于未来的团队" in text

    def _split_name_from_mixed_title(text: str) -> tuple[Optional[str], str]:
        """
        处理类似：
          - "Jon R. Moeller董事会主席 总裁兼首席执行官"
        规则：在第一个中文字符处分割，前半段作为英文姓名，后半段作为中文职务。
        """
        m = re.search(r"[\u4e00-\u9fff]", text)
        if not m:
            return None, text
        name_part = text[: m.start()].strip()
        title_part = text[m.start() :].strip()
        if not name_part:
            return None, text
        return name_part, title_part or text

    for a in soup.find_all("a", href=True):
        href = a["href"]
        # 只关心跳转到 us.pg.com/leadership-team 的卡片链接
        if "us.pg.com/leadership-team" not in href:
            continue
        text = " ".join(a.get_text(strip=True).split())
        if not text:
            continue
        # 去掉“了解更多”
        title_text = text.replace("了解更多", "").strip()

        # 默认从 heading 获取姓名
        heading = a.find_previous(["h2", "h3", "h4"])
        name = None
        if heading:
            heading_text = " ".join(heading.get_text(strip=True).split())
            if heading_text and not _is_generic_heading(heading_text):
                name = heading_text

        # 如 heading 不可靠，则尝试从链接文本中拆分“英文名 + 中文职务”
        if not name:
            maybe_name, maybe_title = _split_name_from_mixed_title(title_text)
            if maybe_name:
                name = maybe_name
                title_text = maybe_title

        if not name:
            continue

        out.append((name, title_text or None))

    return out


def ingest_org_from_page(
    api_base: str,
    company_id: int,
    url: str,
    root_name: str = "管理团队",
) -> None:
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        html = r.text

        parsed = urlparse(url)
        host = parsed.hostname or ""
        path = parsed.path or ""

        people: list[tuple[str, Optional[str]]]
        # 宝洁领导团队页面专用解析
        if host.endswith("pg.com.cn") and "/leadership-team" in path:
            people = parse_people_from_pg_leadership(html)
            if not people:
                # 回退到通用规则
                people = parse_people_from_list_items(html)
        else:
            people = parse_people_from_list_items(html)

        if not people:
            print("未解析到任何姓名/职位，可能需要针对该站点写定制规则。")
            return

        # 创建根部门节点
        root_payload = {
            "company_id": company_id,
            "parent_id": None,
            "node_type": "department",
            "display_name": root_name,
            "sort_order": 0,
            "person_id": None,
        }
        root = client.post(f"{api_base.rstrip('/')}/api/org-nodes", json=root_payload)
        root.raise_for_status()
        root_id = root.json()["id"]

        for idx, (name, title) in enumerate(people):
            person_payload = {
                "company_id": company_id,
                "name": name,
                "title": title,
            }
            pres = client.post(f"{api_base.rstrip('/')}/api/people", json=person_payload)
            pres.raise_for_status()
            person_id = pres.json()["id"]

            node_payload = {
                "company_id": company_id,
                "parent_id": root_id,
                "node_type": "person",
                "display_name": f"{title or '负责人'} / {name}",
                "sort_order": idx,
                "person_id": person_id,
            }
            nres = client.post(f"{api_base.rstrip('/')}/api/org-nodes", json=node_payload)
            nres.raise_for_status()

        print(f"已从 {url} 解析并写入 {len(people)} 位负责人到公司 {company_id}")


def main() -> None:
    ap = argparse.ArgumentParser(description="从管理团队页面解析负责人并写入组织架构（含宝洁定制规则）")
    ap.add_argument("--api", required=True, help="后端 API base，如 http://127.0.0.1:8000")
    ap.add_argument("--company-id", required=True, type=int, help="目标公司 ID")
    ap.add_argument("--url", required=True, help="管理团队/组织架构页面 URL")
    ap.add_argument("--root-name", default="管理团队", help="根节点名称（默认：管理团队）")
    args = ap.parse_args()

    ingest_org_from_page(
        api_base=args.api,
        company_id=args.company_id,
        url=args.url,
        root_name=args.root_name,
    )


if __name__ == "__main__":
    main()

