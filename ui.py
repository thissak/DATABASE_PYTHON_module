import os
import sys
import json
import datetime
import subprocess
from PyQt5.QtWidgets import (
    QMainWindow, QTreeWidget, QTextEdit, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QMessageBox, QRadioButton, QGroupBox, QPushButton
)
from PyQt5.QtGui import QFont, QPixmap, QBrush, QColor
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices

from tree_manager import files_dict, display_part_info, apply_tree_view_styles

# ─────────────────────────────────────────────────────────────
# ClickableLabel: 클릭 이벤트 처리가 가능한 QLabel 하위 클래스
# ─────────────────────────────────────────────────────────────
class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

# ─────────────────────────────────────────────────────────────
# MyTreeWidget: 드래그 앤 드롭 및 노드 검색 기능 제공
# ─────────────────────────────────────────────────────────────
class MyTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
    
    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            main_window = self.window()
            if hasattr(main_window, "on_tree_item_double_clicked"):
                main_window.on_tree_item_double_clicked(item, 0)
        event.ignore()
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            main_window = self.window()
            not_found_files = []  # 찾지 못한 파일 리스트

            for url in event.mimeData().urls():
                file_name_no_ext = os.path.splitext(os.path.basename(url.toLocalFile()))[0]
                parts = file_name_no_ext.split("_")
                part_number = parts[3] if len(parts) >= 4 else file_name_no_ext  # 파트넘버 추출
                item = self.find_item(part_number)

                if item:
                    self.setCurrentItem(item)
                    item.setExpanded(True)
                    if hasattr(main_window, "on_tree_item_clicked"):
                        main_window.on_tree_item_clicked(item, 0)
                else:
                    not_found_files.append(file_name_no_ext)

            if not_found_files:
                QMessageBox.warning(
                    self, "파일 노드 없음",
                    "다음 파일과 일치하는 노드를 찾을 수 없습니다:\n\n" + "\n".join(not_found_files),
                    QMessageBox.Ok
                )
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def find_item(self, text):
        def recursive_search(item):
            if item.text(0) == text:
                return item
            for i in range(item.childCount()):
                found = recursive_search(item.child(i))
                if found:
                    return found
            return None
        
        for i in range(self.topLevelItemCount()):
            found = recursive_search(self.topLevelItem(i))
            if found:
                return found
        return None

# ─────────────────────────────────────────────────────────────
# MainWindow: 메인 윈도우 (트리, 로그, 이미지, 필터, 메모)
# ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Parts Treeview + Drag&Drop + Image Panel")
        self.resize(1000, 1600)
        self.current_part_no = None   # 현재 선택된 파트넘버
        self.memo_data = {}           # 메모 저장용 딕셔너리 (파트번호: { "memo": 내용, "timestamp": 시간 })
        self.json_file_path = None    # JSON 파일 경로 (예: 01_excel/memo.json)
        self.df = None                # Excel 데이터 (build_tree_view에서 설정)
        self.init_ui()
    
    def init_ui(self):
        # ─── 좌측: 트리뷰 + 로그창 ──────────────────────────────
        self.tree = MyTreeWidget()
        self.tree.setColumnCount(1)
        self.tree.setHeaderLabels(["FA-50M FINAL ASSEMBLY VERSION POLAND"])
        self.tree.itemClicked.connect(self.on_tree_item_clicked)
        self.tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        
        self.logText = QTextEdit()
        self.logText.setReadOnly(True)
        self.logText.setFixedHeight(300)
        
        leftLayout = QVBoxLayout()
        leftLayout.addWidget(self.tree, stretch=3)
        leftLayout.addWidget(self.logText, stretch=1)
        leftWidget = QWidget()
        leftWidget.setLayout(leftLayout)
        
        # ─── 우측 상단: 이미지 패널 ──────────────────────────────
        self.imageLabel = ClickableLabel("이미지가 여기에 표시됩니다.", self)
        self.imageLabel.setAlignment(Qt.AlignHCenter | Qt.AlignCenter)
        self.imageLabel.setStyleSheet("border: 1px solid gray;")
        self.imageLabel.setFixedSize(400, 400)
        self.imageLabel.clicked.connect(self.load_image_for_current_part)
        
        # ─── 공통 스타일 ───────────────────────────────────────
        qgroupbox_style = (
            "QGroupBox { background-color: #f0f0f0; border: 1px solid gray; margin-top: 10px; }"
            "QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; font-weight: bold; }"
        )
        button_style = """
            QPushButton {
                background-color: lightgray;
                border: 2px solid gray;
                border-radius: 5px;
                padding: 8px;
                font-size: 20px;
            }
            QPushButton:checked, QPushButton:pressed {
                background-color: yellow;
                border: 2px solid orange;
            }
        """
        
        # ─── 라디오 버튼 그룹 + Filter 버튼 ───────────────────
        self.radio_image = QRadioButton("Image")
        self.radio_3dxml = QRadioButton("3DXML")
        self.radio_fbx = QRadioButton("FBX")
        self.radio_image.setChecked(True)
        self.radio_image.toggled.connect(self.on_radio_image_clicked)
        self.radio_3dxml.toggled.connect(self.on_radio_3dxml_clicked)
        self.radio_fbx.toggled.connect(self.on_radio_fbx_clicked)
        
        self.filter_button = QPushButton("Filter")
        self.filter_button.setCheckable(True)
        self.filter_button.toggled.connect(self.on_filter_button_toggled)
        self.filter_button.setMinimumSize(130, 40)
        self.filter_button.setStyleSheet(button_style)
        
        # 라디오 버튼들 가로 배치
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.radio_image)
        radio_layout.addWidget(self.radio_3dxml)
        radio_layout.addWidget(self.radio_fbx)
        radio_layout.setAlignment(Qt.AlignCenter)
        
        # 필터 버튼 중앙 정렬
        filter_layout = QHBoxLayout()
        filter_layout.addStretch()
        filter_layout.addWidget(self.filter_button)
        filter_layout.addStretch()
        
        radio_main_layout = QVBoxLayout()
        radio_main_layout.addLayout(radio_layout)
        radio_main_layout.addLayout(filter_layout)
        
        self.radio_group = QGroupBox("Select mode")
        self.radio_group.setStyleSheet(qgroupbox_style)
        self.radio_group.setFixedHeight(180)
        self.radio_group.setLayout(radio_main_layout)
        
        # ─── 메모 그룹 ─────────────────────────────────────────
        self.memo_group = QGroupBox("Memo")
        self.memo_group.setStyleSheet(qgroupbox_style)
        memo_layout = QVBoxLayout()

        # 버튼 레이아웃 (Save Memo, Clear Memo)
        button_layout = QHBoxLayout()
        self.memoSaveButton = QPushButton("Save Memo")
        self.memoSaveButton.clicked.connect(self.on_save_memo)
        self.memoSaveButton.setStyleSheet(button_style)

        self.memoClearButton = QPushButton("Clear Memo")
        self.memoClearButton.clicked.connect(self.on_clear_memo)
        self.memoClearButton.setStyleSheet(button_style)
        button_layout.addWidget(self.memoSaveButton)
        button_layout.addWidget(self.memoClearButton)

        # 읽기 전용 텍스트 출력 박스 (메모 출력용)
        self.memoOutput = QTextEdit()
        self.memoOutput.setReadOnly(True)
        self.memoOutput.setFixedHeight(150)
        self.memoOutput.setStyleSheet("QTextEdit { background-color: #e0e0e0; }")

        # 메모 입력 박스 (사용자 입력 전용)
        self.memoText = QTextEdit()
        self.memoText.setFixedHeight(150)
        self.memoText.setStyleSheet("QTextEdit { text-align: left; }")
        self.memoText.setAlignment(Qt.AlignLeft)

        # 레이아웃 순서: 출력박스 -> 입력박스 -> 버튼
        memo_layout.addWidget(self.memoOutput)
        memo_layout.addWidget(self.memoText)
        memo_layout.addLayout(button_layout)
        self.memo_group.setLayout(memo_layout)
        self.memo_group.setFixedHeight(480)

        # ─── 우측 전체 레이아웃 ─────────────────────────────
        rightLayout = QVBoxLayout()
        rightLayout.addWidget(self.imageLabel)
        rightLayout.addWidget(self.radio_group)
        rightLayout.addWidget(self.memo_group)
        rightWidget = QWidget()
        rightWidget.setLayout(rightLayout)
        
        # ─── 메인 레이아웃 ─────────────────────────────
        mainLayout = QHBoxLayout()
        mainLayout.addWidget(leftWidget, stretch=4)
        mainLayout.addWidget(rightWidget, stretch=3)
        centralWidget = QWidget()
        centralWidget.setLayout(mainLayout)
        self.setCentralWidget(centralWidget)
    
    # ─── 필터 관련 함수 ─────────────────────────────
    def filter_tree_items(self, tree_widget, mode):
        def filter_item(item):
            part_no = item.text(0).upper()
            visible_child = any(filter_item(item.child(i)) for i in range(item.childCount()))
            visible_self = part_no in files_dict[mode]
            visible = visible_self or visible_child
            item.setHidden(not visible)
            return visible
        for i in range(tree_widget.topLevelItemCount()):
            filter_item(tree_widget.topLevelItem(i))
    
    def clear_tree_filter(self, tree_widget):
        def clear_item(item):
            item.setHidden(False)
            for i in range(item.childCount()):
                clear_item(item.child(i))
        for i in range(tree_widget.topLevelItemCount()):
            clear_item(tree_widget.topLevelItem(i))
    
    def on_filter_button_toggled(self, checked):
        if checked:
            if self.radio_image.isChecked():
                mode = "image"
            elif self.radio_3dxml.isChecked():
                mode = "xml3d"
            elif self.radio_fbx.isChecked():
                mode = "fbx"
            else:
                mode = "image"
            self.filter_tree_items(self.tree, mode)
            self.appendLog(f"Filter applied: {mode}")
        else:
            self.clear_tree_filter(self.tree)
            self.appendLog("Filter cleared")
    
    # ─── JSON 메모 로드/저장 ─────────────────────────────
    def load_memo_data(self):
        if not os.path.exists(self.json_file_path):
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
            self.memo_data = {}
        else:
            try:
                with open(self.json_file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:  # 파일이 비어있으면
                        self.memo_data = {}
                    else:
                        self.memo_data = json.loads(content)
            except json.JSONDecodeError:
                # JSON 오류 발생 시 빈 딕셔너리로 초기화
                self.memo_data = {}
    
    def save_memo_data(self):
        try:
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.memo_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "에러", f"JSON 파일 저장 중 오류: {str(e)}")
    
    # ─── 라디오 버튼 및 기타 슬롯 함수 ─────────────────────────────
    def on_radio_image_clicked(self, checked):
        if checked:
            apply_tree_view_styles(self.tree, "image")
            if self.filter_button.isChecked():
                self.reset_filter_button()
    
    def on_radio_3dxml_clicked(self, checked):
        if checked:
            apply_tree_view_styles(self.tree, "3dxml")
            if self.filter_button.isChecked():
                self.reset_filter_button()
    
    def on_radio_fbx_clicked(self, checked):
        if checked:
            apply_tree_view_styles(self.tree, "fbx")
            if self.filter_button.isChecked():
                self.reset_filter_button()
    
    def reset_filter_button(self):
        if self.filter_button.isChecked():
            self.filter_button.setChecked(False)
    
    def appendLog(self, message):
        self.logText.append(message)
    
    def load_image_for_current_part(self):
        part_no = self.current_part_no
        if part_no in files_dict["image"]:
            image_path = files_dict["image"][part_no]
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        self.imageLabel.width(),
                        self.imageLabel.height(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.imageLabel.setPixmap(scaled)
                else:
                    self.imageLabel.clear()
                    self.imageLabel.setText("이미지 로드 실패.")
            else:
                self.imageLabel.clear()
                self.imageLabel.setText("이미지가 없습니다.")
        else:
            self.imageLabel.clear()
            self.imageLabel.setText("이미지가 없습니다.")
    
    def on_tree_item_clicked(self, item, column):
        part_no = item.text(column).strip().upper()
        self.current_part_no = part_no
        display_part_info(part_no, self)
        self.load_image_for_current_part()
        
        # 저장된 메모가 있다면, 읽기 전용 출력 박스에 출력
        if part_no in self.memo_data:
            memo_entries = self.memo_data[part_no]
            if isinstance(memo_entries, list):
                display_text = "\n".join(
                    f"[{entry.get('timestamp', '').strip()}] {entry.get('memo', '').strip()}"
                    for entry in memo_entries
                )
            elif isinstance(memo_entries, dict):
                display_text = f"[{memo_entries.get('timestamp', '').strip()}] {memo_entries.get('memo', '').strip()}"
            else:
                display_text = str(memo_entries)
            self.memoOutput.setPlainText(display_text)
        else:
            self.memoOutput.clear()
        
        # 메모 입력 박스는 항상 클리어 (입력 전용)
        self.memoText.clear()
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.appendLog(f"[{timestamp}] Node clicked: {part_no}")
        
        # 메모 입력창은 항상 빈 상태로 유지 (입력 전용)
        self.memoText.clear()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.appendLog(f"[{timestamp}] Node clicked: {part_no}")

    def on_tree_item_double_clicked(self, item, column):
        part_no = item.text(column).strip().upper()
        if self.radio_image.isChecked():
            if part_no in files_dict["image"]:
                image_path = files_dict["image"][part_no]
                if os.path.exists(image_path):
                    QDesktopServices.openUrl(QUrl.fromLocalFile(image_path))
                else:
                    QMessageBox.warning(self, "경고", "이미지 파일이 존재하지 않습니다.")
            else:
                QMessageBox.warning(self, "경고", "해당 파트넘버에 해당하는 이미지가 없습니다.")
        elif self.radio_3dxml.isChecked():
            if part_no in files_dict["xml3d"]:
                xml_path = files_dict["xml3d"][part_no]
                if os.path.exists(xml_path):
                    try:
                        cmd = f'cmd /c start "" "{xml_path}"'
                        subprocess.run(cmd, shell=True, check=True)
                    except Exception as e:
                        QMessageBox.warning(self, "에러", f"3DXML 파일 실행 오류: {str(e)}")
                else:
                    QMessageBox.warning(self, "경고", "3DXML 파일이 존재하지 않습니다.")
            else:
                QMessageBox.warning(self, "경고", "해당 파트넘버에 해당하는 3DXML 파일이 없습니다.")
        elif self.radio_fbx.isChecked():
            if part_no in files_dict["fbx"]:
                fbx_path = files_dict["fbx"][part_no]
                if os.path.exists(fbx_path):
                    try:
                        cmd = f'cmd /c start "" "{fbx_path}"'
                        subprocess.run(cmd, shell=True, check=True)
                    except Exception as e:
                        QMessageBox.warning(self, "에러", f"FBX 파일 실행 오류: {str(e)}")
                else:
                    QMessageBox.warning(self, "경고", "FBX 파일이 존재하지 않습니다.")
            else:
                QMessageBox.warning(self, "경고", "해당 파트넘버에 해당하는 FBX 파일이 없습니다.")
    
    def on_save_memo(self):
        if not self.current_part_no:
            QMessageBox.warning(self, "경고", "먼저 파트를 선택하세요.")
            return
        memo_content = self.memoText.toPlainText().strip()
        if not memo_content:
            QMessageBox.information(self, "알림", "메모를 입력하세요.")
            return
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_entry = {"memo": memo_content, "timestamp": timestamp}
        
        # 여러 메모를 리스트로 저장하도록 처리
        if self.current_part_no in self.memo_data:
            if not isinstance(self.memo_data[self.current_part_no], list):
                self.memo_data[self.current_part_no] = [self.memo_data[self.current_part_no]]
            self.memo_data[self.current_part_no].append(new_entry)
        else:
            self.memo_data[self.current_part_no] = [new_entry]
        
        self.save_memo_data()
        self.appendLog(f"[{timestamp}] Saved Memo for {self.current_part_no}: {memo_content}")
        
        # 입력 박스 클리어 후, 출력 박스 업데이트
        self.memoText.clear()
        # 업데이트: 출력 박스에 해당 노드의 모든 메모 출력
        memo_entries = self.memo_data[self.current_part_no]
        display_text = "\n\n".join(
            f"[{entry.get('timestamp', '').strip()}] {entry.get('memo', '').strip()}"
            for entry in memo_entries
        )
        self.memoOutput.setPlainText(display_text)


    def on_clear_memo(self):
        if not self.current_part_no:
            QMessageBox.warning(self, "경고", "먼저 파트를 선택하세요.")
            return
        confirm = QMessageBox.question(
            self, "메모 삭제", f"'{self.current_part_no}'의 메모를 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.No:
            return
        # 입력용 메모창과 출력용 메모창 모두 클리어
        self.memoText.clear()
        self.memoOutput.clear()

        # JSON 데이터에서도 해당 파트 메모 삭제
        if self.current_part_no in self.memo_data:
            del self.memo_data[self.current_part_no]
            self.save_memo_data()
        self.appendLog(f"Cleared Memo - Node: {self.current_part_no}")
