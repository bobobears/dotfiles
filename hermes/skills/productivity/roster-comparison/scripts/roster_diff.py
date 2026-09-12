#!/usr/bin/env python3
"""roster_diff.py — 对比两份名册/名单表格，按身份证号找出新增和减少的人员。

用法:
    python roster_diff.py OLD NEW [--password PW] [--json OUT.json]

自动探测格式（扩展名不可信）:
    zip 头            -> xlsx (openpyxl)
    OLE2 + EncryptedPackage -> 加密文件, 需 --password (msoffcrypto-tool)
    OLE2 其他         -> 旧版 .xls (xlrd)

自动定位表头行（同时含"姓名"与"身份证/证件号"的行），数据从下一行开始，
跳过空姓名行。输出中文摘要 + 可选 JSON。

依赖: pip install openpyxl xlrd msoffcrypto-tool olefile
"""
import argparse
import io
import json
import sys
from collections import Counter


def sniff(path):
    """返回 'xlsx' | 'encrypted' | 'xls'（按文件头，不看扩展名）。"""
    with open(path, "rb") as f:
        head = f.read(8)
    if head[:4] == b"PK\x03\x04":
        return "xlsx"
    if head[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        try:
            import olefile
            ole = olefile.OleFileIO(path)
            entries = ["/".join(e) for e in ole.listdir()]
            ole.close()
        except Exception:
            entries = []
        if any("EncryptedPackage" in e or "EncryptionInfo" in e for e in entries):
            return "encrypted"
        return "xls"
    raise SystemExit(f"无法识别的文件格式: {path} (head={head[:8]!r})")


def decrypt(path, password):
    import msoffcrypto
    with open(path, "rb") as f:
        of = msoffcrypto.OfficeFile(f)
        if not of.is_encrypted():
            return path
        of.load_key(password=password)  # 密码错误会抛异常
        out = io.BytesIO()
        of.decrypt(out)
    tmp = "/tmp/roster_decrypted_" + __import__("os").path.basename(path)
    with open(tmp, "wb") as f:
        f.write(out.getvalue())
    return tmp


def norm_id(v):
    """身份证归一化：去空白、转大写；float 去掉 .0。"""
    if v is None:
        return ""
    s = str(v).strip().upper()
    if not s:
        return ""
    # float 精度丢失信号（18位 > float53）
    if "E" in s or ("." in s and not s.endswith(".0")):
        return s + "\u26a0"  # 标记，后续提示用户核对
    if s.endswith(".0"):
        s = s[:-2]
    return s


def read_rows(path, fmt):
    """返回 (rows, name_col, id_col)；rows 为 list[list[str]]。"""
    if fmt == "xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb[wb.sheetnames[0]]
        rows = [[("" if c is None else str(c)) for c in r]
                for r in ws.iter_rows(values_only=True)]
    elif fmt == "xls":
        import xlrd
        sh = xlrd.open_workbook(path).sheet_by_index(0)
        rows = [[str(sh.cell_value(i, j)) for j in range(sh.ncols)]
                for i in range(sh.nrows)]
    else:
        raise SystemExit(f"不支持的格式: {fmt}")

    # 定位表头行：同时含 姓名 与 (身份证|证件号)
    header_idx = name_col = id_col = None
    for i, row in enumerate(rows[:10]):
        joined = [c.strip() for c in row]
        n = next((j for j, c in enumerate(joined) if "姓名" in c and "监护人" not in c), None)
        d = next((j for j, c in enumerate(joined) if ("身份证" in c or "证件号" in c)), None)
        if n is not None and d is not None:
            header_idx, name_col, id_col = i, n, d
            break
    if header_idx is None:
        raise SystemExit("未找到表头行（需同时含'姓名'与'身份证/证件号'列）")

    data = []
    for row in rows[header_idx + 1:]:
        name = row[name_col].strip() if name_col < len(row) else ""
        idc = norm_id(row[id_col]) if id_col < len(row) else ""
        if not name:
            continue
        data.append({"name": name, "idcard": idc})
    return data


def diff(old, new):
    old_ids = {p["idcard"]: p["name"] for p in old}
    new_ids = {p["idcard"]: p["name"] for p in new}
    added = [new_ids[i] + "  " + i for i in new_ids if i not in old_ids]
    removed = [old_ids[i] + "  " + i for i in old_ids if i not in new_ids]

    # 交叉验证：同姓名不同证号（疑似录入笔误）
    old_names, new_names = Counter(p["name"] for p in old), Counter(p["name"] for p in new)
    suspects = []
    for p in new:
        if p["name"] in old_names and p["idcard"] not in old_ids:
            match = [q for q in old if q["name"] == p["name"]]
            suspects.append(f"{p['name']}: 旧表 {match[0]['idcard']} vs 新表 {p['idcard']}")
    return added, removed, suspects


def main():
    ap = argparse.ArgumentParser(description="名册对比：按身份证号找新增/减少人员")
    ap.add_argument("old", help="旧表路径（如 5月）")
    ap.add_argument("new", help="新表路径（如 8月）")
    ap.add_argument("--password", default=None, help="加密文件的打开密码")
    ap.add_argument("--json", dest="json_out", default=None, help="结果另存 JSON")
    args = ap.parse_args()

    fmt_old, fmt_new = sniff(args.old), sniff(args.new)
    if fmt_old == "encrypted" or fmt_new == "encrypted":
        if not args.password:
            raise SystemExit("文件已加密（WPS/Excel 密码保护），请用 --password 提供打开密码")
    path_old = decrypt(args.old, args.password) if fmt_old == "encrypted" else args.old
    path_new = decrypt(args.new, args.password) if fmt_new == "encrypted" else args.new

    old = read_rows(path_old, "xlsx" if fmt_old in ("xlsx", "encrypted") else "xls")
    new = read_rows(path_new, "xlsx" if fmt_new in ("xlsx", "encrypted") else "xls")

    for label, lst in (("旧表", old), ("新表", new)):
        dups = {k: v for k, v in Counter(p["idcard"] for p in lst).items() if v > 1}
        bad = [p["name"] for p in lst if "\u26a0" in p["idcard"]]
        print(f"{label}: {len(lst)} 人 | 重复证号: {dups or '无'} | "
              f"疑似精度丢失(需核对原件): {bad or '无'}")

    added, removed, suspects = diff(old, new)
    print(f"\n===== 新增（{len(added)} 人）=====")
    for line in added:
        print("  " + line)
    print(f"===== 减少（{len(removed)} 人）=====")
    for line in removed:
        print("  " + line)
    if suspects:
        print("\n⚠️ 同姓名不同证号（疑似录入笔误，请人工确认是否同一人）:")
        for s in suspects:
            print("  " + s)

    # 数量恒等式校验
    expect = len(old) - len(removed) + len(added)
    if expect != len(new):
        print(f"\n⚠️ 数量核对不平: {len(old)} - {len(removed)} + {len(added)} "
              f"= {expect} ≠ 新表 {len(new)}（可能存在重复证号）")

    if args.json_out:
        json.dump({"old_count": len(old), "new_count": len(new),
                   "added": added, "removed": removed, "suspects": suspects},
                  open(args.json_out, "w"), ensure_ascii=False, indent=2)
        print(f"\nJSON 已写入: {args.json_out}")


if __name__ == "__main__":
    main()
