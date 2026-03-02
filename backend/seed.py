from __future__ import annotations

import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.app.db import init_db, session
from backend.app.models import Company, OrgNode, OrgNodeType, Person


def main() -> None:
    init_db()
    with session() as s:
        c = Company(name="示例：某美妆快消集团", industry="美妆/快消", website="https://example.com")
        s.add(c)
        s.commit()
        s.refresh(c)

        ceo = Person(company_id=c.id, name="李某某", title="总经理", phones='["13800000000"]', source_confidence=0.6)
        head_mkt = Person(company_id=c.id, name="王某某", title="市场负责人", phones='["13900000000"]', source_confidence=0.6)
        head_sales = Person(company_id=c.id, name="赵某某", title="渠道负责人", phones='["13700000000"]', source_confidence=0.6)
        s.add(ceo)
        s.add(head_mkt)
        s.add(head_sales)
        s.commit()
        s.refresh(ceo)
        s.refresh(head_mkt)
        s.refresh(head_sales)

        n_root = OrgNode(company_id=c.id, parent_id=None, node_type=OrgNodeType.department, display_name="总部", sort_order=0)
        s.add(n_root)
        s.commit()
        s.refresh(n_root)

        n_ceo = OrgNode(
            company_id=c.id,
            parent_id=n_root.id,
            node_type=OrgNodeType.person,
            display_name="总经理 / 李某某",
            sort_order=0,
            person_id=ceo.id,
        )
        n_mkt = OrgNode(company_id=c.id, parent_id=n_root.id, node_type=OrgNodeType.department, display_name="市场部", sort_order=10)
        n_sales = OrgNode(company_id=c.id, parent_id=n_root.id, node_type=OrgNodeType.department, display_name="销售部", sort_order=20)
        s.add(n_ceo)
        s.add(n_mkt)
        s.add(n_sales)
        s.commit()
        s.refresh(n_mkt)
        s.refresh(n_sales)

        s.add(
            OrgNode(
                company_id=c.id,
                parent_id=n_mkt.id,
                node_type=OrgNodeType.person,
                display_name="市场负责人 / 王某某",
                sort_order=0,
                person_id=head_mkt.id,
            )
        )
        s.add(
            OrgNode(
                company_id=c.id,
                parent_id=n_sales.id,
                node_type=OrgNodeType.person,
                display_name="渠道负责人 / 赵某某",
                sort_order=0,
                person_id=head_sales.id,
            )
        )
        s.commit()

    print("seed done. open http://127.0.0.1:8000/ui")


if __name__ == "__main__":
    main()

