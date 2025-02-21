import os
import sys
import time
import subprocess
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QMessageBox,
    QRadioButton
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices

# modules.py에서 필요한 함수와 전역 변수 가져오기
from modules import (
    get_base_path, build_tree_view, image_dict, xml3d_dict, display_part_info
)

# ─────────────────────────────────────────────────────────────
# ClickableLabel: 클릭 이벤트를 처리할 수 있는 QLabel 하위 클래스
# ─────────────────────────────────────────────────────────────
class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

# ─────────────────────────────────────────────────────────────
# MyTreeWidget: 드래그앤드롭 및 노드 검색 기능 제공
# ─────────────────────────────────────────────────────────────
class MyTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
    
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
# MainWindow: 트리뷰, 로그창, 이미지 패널 및 라디오 버튼 포함
# ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Parts Treeview + Drag&Drop + Image Panel")
        self.resize(1000, 1600)
        
        self.df = None  # 엑셀 데이터 저장
        self.current_part_no = None  # 현재 선택된 파트넘버 저장
        
        self.tree = MyTreeWidget()
        self.tree.setColumnCount(1)
        self.tree.setHeaderLabels(["FA-50M FINAL ASSEMBLY VERSION POLAND"])
        self.tree.itemClicked.connect(self.on_tree_item_clicked)
        self.tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        
        # 로그창 생성
        self.logText = QTextEdit()
        self.logText.setReadOnly(True)
        self.logText.setFixedHeight(300)
        
        # 이미지 패널 (ClickableLabel)
        self.imageLabel = ClickableLabel("이미지가 여기에 표시됩니다.", self)
        self.imageLabel.setAlignment(Qt.AlignHCenter | Qt.AlignCenter)
        self.imageLabel.setStyleSheet("border: 1px solid gray;")
        self.imageLabel.setFixedSize(400, 400)
        self.imageLabel.clicked.connect(self.load_image_for_current_part)
        
        # 라디오 버튼 생성
        self.radio_image = QRadioButton("Image")
        self.radio_3dxml = QRadioButton("3DXML")
        self.radio_image.setChecked(True)  # 기본값 Image
        
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.radio_image)
        radio_layout.addWidget(self.radio_3dxml)
        radio_container = QWidget()
        radio_container.setLayout(radio_layout)
        
        # 레이아웃 구성
        rightLayout = QVBoxLayout()
        rightLayout.addWidget(self.imageLabel)
        rightLayout.addWidget(radio_container)
        rightWidget = QWidget()
        rightWidget.setLayout(rightLayout)
        
        leftLayout = QVBoxLayout()
        leftLayout.addWidget(self.tree, stretch=3)
        leftLayout.addWidget(self.logText, stretch=1)
        leftWidget = QWidget()
        leftWidget.setLayout(leftLayout)
        
        mainLayout = QHBoxLayout()
        mainLayout.addWidget(leftWidget, stretch=4)
        mainLayout.addWidget(rightWidget, stretch=3)
        centralWidget = QWidget()
        centralWidget.setLayout(mainLayout)
        self.setCentralWidget(centralWidget)
    
    def appendLog(self, message):
        self.logText.append(message)
    
    def on_tree_item_clicked(self, item, column):
        """트리 노드 클릭 시 동작"""
        part_no = item.text(column).strip().upper()
        self.current_part_no = part_no  # 현재 선택된 파트넘버 저장
        
        # Excel 메타데이터 출력
        display_part_info(part_no, self)
        
        # 클릭 시 이미지 표시
        self.load_image_for_current_part()
    
    def load_image_for_current_part(self):
        """현재 선택된 파트넘버에 해당하는 이미지를 이미지 패널에 로드"""
        part_no = self.current_part_no
        
        if part_no in image_dict:
            image_path = image_dict[part_no]
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
        """트리 노드 더블클릭 시 동작"""
        part_no = item.text(column).strip().upper()

        if self.radio_image.isChecked():
            # 이미지 모드: 이미지 파일을 기본 뷰어로 열기
            if part_no in image_dict:
                image_path = image_dict[part_no]
                if os.path.exists(image_path):
                    QDesktopServices.openUrl(QUrl.fromLocalFile(image_path))
                else:
                    QMessageBox.warning(self, "경고", "이미지 파일이 존재하지 않습니다.")
            else:
                QMessageBox.warning(self, "경고", "해당 파트넘버에 해당하는 이미지가 없습니다.")

        elif self.radio_3dxml.isChecked():
            # 3DXML 모드: Windows 기본 연결 프로그램으로 실행
            if part_no in xml3d_dict:
                xml_path = xml3d_dict[part_no]
                if os.path.exists(xml_path):
                    try:
                        # CMD에서 'start "" "전체 경로"'로 실행하던 방식을 그대로 사용
                        cmd = f'cmd /c start "" "{xml_path}"'
                        subprocess.run(cmd, shell=True, check=True)
                    except Exception as e:
                        QMessageBox.warning(self, "에러", f"3DXML 파일 실행 오류: {str(e)}")
                else:
                    QMessageBox.warning(self, "경고", "3DXML 파일이 존재하지 않습니다.")
            else:
                QMessageBox.warning(self, "경고", "해당 파트넘버에 해당하는 3DXML 파일이 없습니다.")







# ─────────────────────────────────────────────────────────────
# 메인 실행 함수
# ─────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    # 엑셀 파일 로드
    base_path = get_base_path()
    excelfolder_path = os.path.join(base_path, "01_excel")
    excel_file_path = os.path.join(excelfolder_path, "data.xlsx")
    
    if os.path.exists(excel_file_path):
        build_tree_view(excel_file_path, window)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
