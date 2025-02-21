import os
import sys
import time
import pandas as pd
from PyQt5.QtWidgets import QTreeWidgetItem, QMessageBox, QHeaderView  # QTreeWidgetItem import 추가
from PyQt5.QtGui import QPixmap, QBrush, QColor
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices

# ─────────────────────────────────────────────────────────────
# 전역 변수들
# ─────────────────────────────────────────────────────────────
nodeCount = 0
g_NodeDictionary = {}  # 파트넘버 -> 트리 아이템
image_dict = {}        # 파트넘버 -> 이미지 파일 경로
xml3d_dict = {}        # 3DXML 파일 경로 저장

def get_base_path():
    """실행 파일(또는 스크립트)이 있는 폴더를 반환"""
    if getattr(sys, 'frozen', False):  # PyInstaller로 빌드된 경우
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

def build_xml3d_dict(window):
    """
    02_3dxml 폴더에서 .3dxml 파일을 스캔하여,
    파일명 예: aaa_bbb_ccc_PARTNO.3dxml 의 형식이라고 가정하고,
    PARTNO를 추출하여 xml3d_dict[PARTNO] = 파일 경로 로 저장.
    """
    xml3d_dict.clear()  # 기존 데이터 초기화

    base_path = get_base_path()  
    folder_path = os.path.join(base_path, "02_3dxml")  # 3DXML 파일 폴더

    if not os.path.exists(folder_path):
        window.appendLog(f"[build_xml3d_dict] 02_3dxml 폴더를 찾을 수 없습니다: {folder_path}")
        return
    
    for fname in os.listdir(folder_path):
        lower_name = fname.lower()
        if lower_name.endswith(".3dxml"):
            file_parts = fname.split("_")
            if len(file_parts) >= 4:
                part_number = os.path.splitext(file_parts[3])[0].upper()
                if part_number not in xml3d_dict:
                    xml3d_dict[part_number] = os.path.join(folder_path, fname)
    # 개별 로그 출력 대신 build_tree_view()에서 최종 요약에 포함합니다.

def build_image_dict(window):
    """
    00_image 폴더에서 PNG/JPG 파일을 스캔하여,
    파일명 예: aaa_bbb_ccc_PARTNO.png 의 형식이라고 가정하고,
    PARTNO를 추출하여 image_dict[PARTNO] = 파일 경로 로 저장.
    """
    image_dict.clear() 
    
    base_path = get_base_path()  # 실행 파일이 있는 폴더 기준으로 경로 설정
    folder_path = os.path.join(base_path, "00_image")
    
    if not os.path.exists(folder_path):
        window.appendLog(f"[build_image_dict] 00_image 폴더를 찾을 수 없습니다: {folder_path}")
        return
    
    for fname in os.listdir(folder_path):
        lower_name = fname.lower()
        if lower_name.endswith(".png") or lower_name.endswith(".jpg"):
            file_parts = fname.split("_")
            if len(file_parts) >= 4:
                # 파일 확장자를 제거하여 파트넘버를 추출합니다.
                part_number = os.path.splitext(file_parts[3])[0]
                if part_number not in image_dict:
                    image_dict[part_number] = os.path.join(folder_path, fname)
    # 개별 로그 출력 대신 build_tree_view()에서 최종 요약에 포함합니다.

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

def apply_tree_view_styles(tree_widget, style):
    """
    라디오버튼 선택에 따라 트리뷰 스타일 적용
    style: "image" 또는 "3dxml"
    """
    def recurse(item):
        part_no = item.text(0)
        # 기본 스타일로 초기화 (볼드 해제 및 검정색)
        font = item.font(0)
        font.setBold(False)
        item.setFont(0, font)
        item.setForeground(0, QBrush(QColor(0, 0, 0)))
        
        if style == "image" and part_no in image_dict:
            font.setBold(True)
            item.setFont(0, font)
            item.setForeground(0, QBrush(QColor(255, 0, 0)))  # 빨간색
        elif style == "3dxml" and part_no in xml3d_dict:
            font.setBold(True)
            item.setFont(0, font)
            item.setForeground(0, QBrush(QColor(0, 0, 255)))  # 파란색

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
    
    # 이미지 및 3DXML 딕셔너리 생성 (내부에서는 딕셔너리만 생성)
    build_image_dict(window)
    build_xml3d_dict(window)
    
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
    
    # 헤더 마지막 컬럼 자동 확장 해제
    header = window.tree.header()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
    
    # 가로 스크롤바 필요시 표시
    window.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    
    g_NodeDictionary = {}
    
    root_item = QTreeWidgetItem(window.tree)
    root_item.setText(0, root_key)
    nodeCount += 1
    node_keys = {root_key: True}
    g_NodeDictionary[root_key] = root_item
    root_item.setExpanded(True)
    
    add_nodes_original(window.tree, root_item, dict_rel, node_keys)
    # 기본 스타일 적용 (예: 기본으로 이미지 스타일 적용)
    apply_tree_view_styles(window.tree, "image")
    
    # 최종 요약정보에 딕셔너리 정보 포함
    summary_log = "===== Operation Summary =====\n"
    summary_log += f"총 이미지 파일 수: {len(image_dict)}\n"
    summary_log += f"총 3DXML 파일 수: {len(xml3d_dict)}\n"
    summary_log += f"총 유효 파트 수: {total_parts}\n"
    summary_log += f"트리뷰에 추가된 전체 노드 수: {nodeCount}\n"
    window.appendLog(summary_log)
    
    elapsed_time = time.time() - start_time
    window.appendLog(f"트리뷰 생성시간: {elapsed_time:.2f} seconds")
