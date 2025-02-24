import os
import sys
import json
import subprocess
from PyQt5.QtWidgets import (
    QMainWindow, QTreeWidget, QTextEdit, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QMessageBox, QRadioButton, QGroupBox, QPushButton
)
from PyQt5.QtGui import QFont, QPixmap
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
            for url in event.mimeData().urls():
                file_name_no_ext = os.path.splitext(os.path.basename(url.toLocalFile()))[0]
                parts = file_name_no_ext.split("_")
                part_number = parts[3] if len(parts) >= 4 else file_name_no_ext
                item = self.find_item(part_number)
                if item:
                    self.setCurrentItem(item)
                    item.setExpanded(True)
                    if hasattr(main_window, "on_tree_item_clicked"):
                        main_window.on_tree_item_clicked(item, 0)
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
# MainWindow: 메인 윈도우 (트리뷰, 로그창, 이미지 패널, 라디오 버튼, 메모창)
# ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Parts Treeview + Drag&Drop + Image Panel")
        self.resize(1000, 1600)
        
        self.current_part_no = None   # 현재 선택된 파트넘버
        self.memo_data = {}           # 메모 저장용 딕셔너리 (파트번호: 메모)
        self.json_file_path = None    # JSON 파일 경로
        self.df = None                # Excel 데이터 (나중에 build_tree_view에서 설정)
        
        self.init_ui()
    
    def init_ui(self):
        # 좌측: 트리뷰와 로그창
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
        
        # 우측: 이미지 패널, 라디오 버튼, 메모창
        self.imageLabel = ClickableLabel("이미지가 여기에 표시됩니다.", self)
        self.imageLabel.setAlignment(Qt.AlignHCenter | Qt.AlignCenter)
        self.imageLabel.setStyleSheet("border: 1px solid gray;")
        self.imageLabel.setFixedSize(400, 400)
        self.imageLabel.clicked.connect(self.load_image_for_current_part)
        
        # 공통 QGroupBox 스타일
        qgroupbox_style = (
            "QGroupBox { background-color: #f0f0f0; border: 1px solid gray; margin-top: 10px; }"
            "QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; font-weight: bold; }"
        )
        
        # 라디오 버튼 그룹 (Image, 3DXML, FBX)
        self.radio_image = QRadioButton("Image")
        self.radio_3dxml = QRadioButton("3DXML")
        self.radio_fbx = QRadioButton("FBX")
        self.radio_image.setChecked(True)
        self.radio_image.toggled.connect(self.on_radio_image_clicked)
        self.radio_3dxml.toggled.connect(self.on_radio_3dxml_clicked)
        self.radio_fbx.toggled.connect(self.on_radio_fbx_clicked)
        
        self.radio_group = QGroupBox("Select mode")
        self.radio_group.setStyleSheet(qgroupbox_style)
        self.radio_group.setFixedHeight(150)
        radio_layout = QHBoxLayout()
        radio_layout.setContentsMargins(5, 5, 5, 5)
        radio_layout.setSpacing(50)
        radio_layout.addWidget(self.radio_image)
        radio_layout.addWidget(self.radio_3dxml)
        radio_layout.addWidget(self.radio_fbx)
        radio_layout.setAlignment(Qt.AlignCenter)
        self.radio_group.setLayout(radio_layout)
        
        # 메모 그룹
        self.memo_group = QGroupBox("Memo")
        self.memo_group.setStyleSheet(qgroupbox_style)
        memo_layout = QVBoxLayout()
        self.memoText = QTextEdit()
        self.memoText.setFixedHeight(450)
        self.memoText.setStyleSheet("QTextEdit { text-align: left; }")
        self.memoText.setAlignment(Qt.AlignLeft)
        self.memoSaveButton = QPushButton("Save Memo")
        self.memoSaveButton.clicked.connect(self.on_save_memo)
        memo_layout.addWidget(self.memoText)
        memo_layout.addWidget(self.memoSaveButton)
        self.memo_group.setLayout(memo_layout)
        
        rightLayout = QVBoxLayout()
        rightLayout.addWidget(self.imageLabel)
        rightLayout.addWidget(self.radio_group)
        rightLayout.addWidget(self.memo_group)
        rightWidget = QWidget()
        rightWidget.setLayout(rightLayout)
        
        mainLayout = QHBoxLayout()
        mainLayout.addWidget(leftWidget, stretch=4)
        mainLayout.addWidget(rightWidget, stretch=3)
        centralWidget = QWidget()
        centralWidget.setLayout(mainLayout)
        self.setCentralWidget(centralWidget)
    
    # JSON 로드/저장 메서드
    def load_memo_data(self):
        if not os.path.exists(self.json_file_path):
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
            self.memo_data = {}
        else:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                self.memo_data = json.load(f)
    
    def save_memo_data(self):
        try:
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.memo_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "에러", f"JSON 파일 저장 중 오류: {str(e)}")
    
    # 슬롯 함수들 (라디오 버튼, 트리 아이템 클릭/더블클릭, 이미지 로드, 메모 저장)
    def on_radio_image_clicked(self, checked):
        if checked:
            apply_tree_view_styles(self.tree, "image")
    
    def on_radio_3dxml_clicked(self, checked):
        if checked:
            apply_tree_view_styles(self.tree, "3dxml")
    
    def on_radio_fbx_clicked(self, checked):
        if checked:
            apply_tree_view_styles(self.tree, "fbx")
    
    def appendLog(self, message):
        self.logText.append(message)
    
    def on_tree_item_clicked(self, item, column):
        part_no = item.text(column).strip().upper()
        self.current_part_no = part_no
        display_part_info(part_no, self)
        self.load_image_for_current_part()
        if part_no in self.memo_data:
            self.memoText.setPlainText(self.memo_data[part_no])
        else:
            self.memoText.clear()
    
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
        memo_content = self.memoText.toPlainText()
        self.memo_data[self.current_part_no] = memo_content
        self.save_memo_data()
        self.appendLog(f"Saved Memo - Node: {self.current_part_no}, Memo: {memo_content}")
