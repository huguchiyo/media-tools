#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
「親フォルダ」に「子フォルダ」の全ファイルが含まれているか確認するスクリプト。

同一判定は**ファイル名（タイトル）のみ**で行います。
子フォルダの各ファイルについて、親フォルダ内（サブフォルダ含む）に
同じファイル名のファイルが 1 つでもあれば「含まれている」とみなします。

使い方:
  python check_subset.py 親フォルダ 子フォルダ
  python check_subset.py "G:/Users/chiyo/Pictures/ふみか" "G:/Users/chiyo/Pictures/ふみひろ_iphone"
"""

import sys
from pathlib import Path

# 写真・動画として扱う拡張子（小文字で比較）
MEDIA_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".heic", ".mov", ".mp4", ".m4v",
    ".avi", ".m2ts", ".mts", ".modd", ".moff", ".aae",
}


def collect_filenames(folder: Path) -> set:
    """フォルダ内の全メディアファイル名を収集（再帰）。Returns: set of file names."""
    names = set()
    if not folder.is_dir():
        return names
    for p in folder.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        names.add(p.name)
    return names


def main():
    # デフォルト: ふみか と ふみひろ_iphone（Pictures 直下を想定）
    pictures = Path(__file__).resolve().parent.parent.parent  # Tools の親の親 = Pictures
    default_parent = pictures / "ふみか"
    default_child = pictures / "ふみひろ_iphone"

    if len(sys.argv) < 3:
        parent_dir = default_parent.resolve()
        child_dir = default_child.resolve()
        print("引数なしのため、デフォルトのフォルダで比較します。")
        print(f"  親: {parent_dir}")
        print(f"  子: {child_dir}")
    else:
        parent_dir = Path(sys.argv[1]).resolve()
        child_dir = Path(sys.argv[2]).resolve()

    if not parent_dir.is_dir():
        print(f"エラー: 親フォルダが見つかりません: {parent_dir}")
        sys.exit(1)
    if not child_dir.is_dir():
        print(f"エラー: 子フォルダが見つかりません: {child_dir}")
        sys.exit(1)

    print("親フォルダのファイル名を収集中...")
    parent_names = collect_filenames(parent_dir)
    print(f"  親フォルダ: {parent_dir}")
    print(f"  メディアファイル数（名前の種類）: {len(parent_names)}")

    print("子フォルダのファイルをチェック中...")
    child_files = [p for p in child_dir.rglob("*") if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS]

    contained = []
    not_contained = []
    for p in child_files:
        if p.name in parent_names:
            contained.append(p)
        else:
            not_contained.append(p)

    # 結果
    print()
    print("=" * 70)
    print("【結果】 ふみひろ_iphone のファイルが ふみか に含まれているか（ファイル名で判定）")
    print("=" * 70)
    print(f"親フォルダ（ふみか）: {parent_dir}")
    print(f"子フォルダ（ふみひろ_iphone）: {child_dir}")
    print()
    print(f"子フォルダのメディアファイル数: {len(child_files)}")
    print(f"  ふみかに含まれている（同じファイル名あり）: {len(contained)} 件")
    print(f"  ふみかに含まれていない: {len(not_contained)} 件")
    print()
    if not_contained:
        print("【ふみかに含まれていないファイル一覧】")
        for p in not_contained:
            rel = p.relative_to(child_dir) if child_dir in p.parents or p.parent == child_dir else p.name
            print(f"  - {rel}")
        print()
    else:
        print("→ ふみひろ_iphone の写真・動画はすべて ふみか に同じファイル名で含まれています。")
    print("=" * 70)


if __name__ == "__main__":
    main()
