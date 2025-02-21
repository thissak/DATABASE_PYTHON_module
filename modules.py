import os
import sys
import time
import pandas as pd
from PyQt5.QtWidgets import QTreeWidgetItem, QMessageBox  # QTreeWidgetItem import 추가
from PyQt5.QtGui import QPixmap, QBrush, QColor
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices

# ─────────────────────────────────────────────────────────────
# 전역 변수들
# ─────────────────────────────────────────────────────────────
nodeCount = 0
g_NodeDictionary = {}  # 파트넘버 -> 트리 아이템
image_dict = {}        # 파트넘버 -> 이미지 파일 경로

def get_base_path():
    """실행 파일(또는 스크립트)이 있는 폴더를 반환"""
    if getattr(sys, 'frozen', False):  # PyInstaller로 빌드된 경우
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

def build_image_dict():
    """
    00_image 폴더 내 PNG/JPG 파일을 스캔하여
    파일명 형식: aaa_bbb_ccc_PARTNO.png
    에서 PARTNO를 추출하여 image_dict[PARTNO] = 파일 경로로 저장
    """
    global image_dict
    image_dict = {}
    
    base_path = get_base_path()
    folder_path = os.path.join(base_path, "00_image")
    
    if not os.path.exists(folder_path):
        print(f"[build_image_dict] 00_image 폴더를 찾을 수 없습니다: {folder_path}")
        return
    
    for fname in os.listdir(folder_path):
        lower_name = fname.lower()
        if lower_name.endswith(".png") or lower_name.endswith(".jpg"):
            file_parts = fname.split("_")
            if len(file_parts) >= 4:
                part_number = file_parts[3]
                if part_number not in image_dict:
                    image_dict[part_number] = os.path.join(folder_path, fname)
    
    print("[build_image_dict] 이미지 딕셔너리 생성 완료.")
    print(f"[build_image_dict] 총 이미지 파일 수: {len(image_dict)}")

def safe_int(value, default="nan"):
    """
    안전하게 int 변환.
    NaN, None, 빈 문자열은 기본값(default)으로 변환
    """
    try:
        if pd.isna(value) or value is None or value == "":
            return default
        return int(value)
    except (ValueError, TypeError):
        return default

def display_part_info(part_no, window):
    """
    엑셀의 메타데이터를 로그창(window.logText)에 출력
    """
    try:
        df = window.df
        if df is None or df.empty:
            window.appendLog("엑셀 데이터가 로드되지 않았습니다.")
            return
        
        if "Part No" not in df.columns:
            raise KeyError("컬럼 'Part No'가 엑셀 데이터에 없습니다. 컬럼명을 확인하세요.")
        
        row = df[df["Part No"].str.strip() == part_no]
        if row.empty:
            window.appendLog(f"해당하는 '{part_no}' 값을 D열에서 찾을 수 없습니다.")
            return
        
        row = row.iloc[0]
        metadataStr = (
            f"S/N: {row.get('S/N', 'N/A')}\n"
            f"Level: {safe_int(row.get('Level', 'N/A'))}\n"
            f"Type: {row.get('Type', 'N/A')}\n"
            f"Part No: {row.get('Part No', 'N/A')}\n"
            f"Part Rev: {row.get('Part Rev', 'N/A')}\n"
            f"Part Status: {row.get('Part Status', 'N/A')}\n"
            f"Latest: {row.get('Latest', 'N/A')}\n"
            f"Nomenclature: {row.get('Nomenclature', 'N/A')}\n"
            f"Instance ID 총수량(ALL DB): {safe_int(row.get('Instance ID 총수량(ALL DB)', 'N/A'))}\n"
            f"Qty: {safe_int(row.get('Qty', 'N/A'))}\n"
            f"NextPart: {row.get('NextPart', 'N/A')}"
        )
        window.logText.clear()
        window.appendLog(metadataStr)
    except Exception as e:
        window.appendLog("에러 발생: " + str(e))

def add_nodes_original(tree_widget, parent_item, dict_rel, node_keys):
    """
    엑셀 데이터 기반 트리뷰 구성용 재귀 함수
    """
    global nodeCount, g_NodeDictionary
    parent_key = parent_item.text(0)
    if parent_key not in dict_rel:
        return
    for child_key in dict_rel[parent_key]:
        new_key = child_key
        is_duplicate = False
        if child_key in node_keys:
            dup_counter = 1
            while new_key in node_keys:
                new_key = f"{child_key}dup{dup_counter}"
                dup_counter += 1
            is_duplicate = True
        node_keys[new_key] = True
        
        # QTreeWidgetItem을 직접 사용합니다.
        child_item = QTreeWidgetItem(parent_item)
        child_item.setText(0, child_key)
        g_NodeDictionary[child_key] = child_item
        
        nodeCount += 1
        if not is_duplicate:
            add_nodes_original(tree_widget, child_item, dict_rel, node_keys)

def apply_tree_view_styles(tree_widget):
    """
    트리뷰에서 image_dict에 해당하는 노드는 볼드 및 빨간색 처리
    """
    def recurse(item):
        part_no = item.text(0)
        if part_no in image_dict:
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            item.setForeground(0, QBrush(QColor(255, 0, 0)))
        for i in range(item.childCount()):
            recurse(item.child(i))
    for i in range(tree_widget.topLevelItemCount()):
        top_item = tree_widget.topLevelItem(i)
        recurse(top_item)
    tree_widget.repaint()

def build_tree_view(excel_path, window):
    """
    엑셀 데이터를 읽어 트리뷰를 구성하는 함수
    """
    global nodeCount, g_NodeDictionary
    start_time = time.time()
    
    build_image_dict()
    
    df = pd.read_excel(excel_path, sheet_name="Sheet1")
    if "PartNo" in df.columns and "NextPart" in df.columns:
        part_nos = df["PartNo"].astype(str).str.strip()
        next_parts = df["NextPart"].astype(str).str.strip()
    else:
        part_nos = df.iloc[:, 3].astype(str).str.strip()
        next_parts = df.iloc[:, 13].astype(str).str.strip()
    
    window.df = df  # 엑셀 데이터를 MainWindow에 저장
    
    total_parts = 0
    nodeCount = 0
    dict_rel = {}
    g_NodeDictionary = {}
    
    final_roots = set()
    for i in range(len(df)):
        part_no = part_nos.iloc[i]
        next_part = next_parts.iloc[i]
        if part_no != "":
            total_parts += 1
            if next_part == "" or next_part.lower() == "nan":
                final_roots.add(part_no)
            else:
                if next_part not in dict_rel:
                    dict_rel[next_part] = []
                dict_rel[next_part].append(part_no)
    
    if len(final_roots) == 0:
        window.appendLog("[build_tree_view] 최종 루트(final root)가 없습니다.")
        return
    root_key = list(final_roots)[0]
    
    window.tree.clear()
    g_NodeDictionary = {}
    
    from PyQt5.QtWidgets import QTreeWidgetItem  # 동적으로 가져오기
    root_item = QTreeWidgetItem(window.tree)
    root_item.setText(0, root_key)
    nodeCount += 1
    node_keys = {root_key: True}
    g_NodeDictionary[root_key] = root_item
    root_item.setExpanded(True)
    
    add_nodes_original(window.tree, root_item, dict_rel, node_keys)
    apply_tree_view_styles(window.tree)
    
    summary_log = "===== Operation Summary =====\n"
    summary_log += f"총 유효 파트 수: {total_parts}\n"
    summary_log += f"트리뷰에 추가된 전체 노드 수: {nodeCount}\n"
    window.appendLog(summary_log)
    
    elapsed_time = time.time() - start_time
    window.appendLog(f"트리뷰 생성시간: {elapsed_time:.2f} seconds")
    print(f"트리뷰 생성시간: {elapsed_time:.2f} seconds")
